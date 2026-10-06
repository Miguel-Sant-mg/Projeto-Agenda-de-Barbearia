import os
import re
import datetime
import socket
from functools import wraps
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
import database

# Carregar variáveis de ambiente do arquivo .env se existir
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

def obter_ip_local():
    """Descobre o IP local da máquina na rede Wi-Fi/Ethernet."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

app = Flask(__name__)

# Configurações de Segurança de Sessão e Cookies
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "arte-de-favela-chave-segura-2026-barbearia")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_COOKIE_SECURE", "false").lower() == "true"
app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(days=7)

# Inicializa o banco de dados e dados padrão
database.criar_banco()

# --- Cabeçalhos de Segurança HTTP ---

@app.after_request
def aplicar_cabecalhos_seguranca(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# --- Decorators de Autenticação ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Por favor, faça login para acessar o painel.", "warning")
            return redirect(url_for("login_view"))
        return f(*args, **kwargs)
    return decorated_function

# --- Filtros de Template Jinja2 ---

@app.template_filter('moeda')
def moeda_filter(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return f"R$ {valor}"

@app.template_filter('data_br')
def data_br_filter(data_str):
    try:
        partes = data_str.split("-")
        if len(partes) == 3:
            return f"{partes[2]}/{partes[1]}/{partes[0]}"
        return data_str
    except Exception:
        return data_str

@app.template_filter('data_extenso')
def data_extenso_filter(data_str):
    try:
        dt = datetime.datetime.strptime(data_str, "%Y-%m-%d")
        dias = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
        nome_dia = dias[dt.weekday()]
        return f"{nome_dia} ({dt.strftime('%d/%m/%Y')})"
    except Exception:
        return data_str

# --- Contexto Global para Templates ---

@app.context_processor
def inject_global_settings():
    configs = database.obter_todas_configuracoes()
    ip_local = obter_ip_local()
    porta = os.environ.get("PORT", "5000")
    return {
        "barbearia_nome": configs.get("nome_barbearia", "Arte de Favela"),
        "barbearia_whatsapp": configs.get("telefone_whatsapp", "(11) 99999-9999"),
        "barbearia_endereco": configs.get("endereco", "Barbearia Arte de Favela"),
        "usuario_logado": session.get("usuario_nome"),
        "ip_local": ip_local,
        "porta_servidor": porta,
        "url_local": f"http://localhost:{porta}",
        "url_celular": f"http://{ip_local}:{porta}"
    }

# ==============================================================================
# ROTAS PÚBLICAS (ÁREA DO CLIENTE)
# ==============================================================================

@app.route("/")
def index():
    servicos = database.listar_servicos(apenas_ativos=True)
    configs = database.obter_todas_configuracoes()
    hoje = datetime.date.today().strftime("%Y-%m-%d")
    return render_template("index.html", servicos=servicos, configs=configs, data_minima=hoje)

@app.route("/api/servicos", methods=["GET"])
def api_servicos():
    servicos = database.listar_servicos(apenas_ativos=True)
    return jsonify(servicos)

@app.route("/api/horarios-disponiveis", methods=["GET"])
def api_horarios_disponiveis():
    data_selecionada = request.args.get("data")
    if not data_selecionada:
        return jsonify({"erro": "Informe o parâmetro 'data' (YYYY-MM-DD)"}), 400

    # Validar formato da data
    try:
        datetime.datetime.strptime(data_selecionada, "%Y-%m-%d")
    except ValueError:
        return jsonify({"erro": "Formato de data inválido. Use YYYY-MM-DD"}), 400

    aberto = database.dia_da_semana_aberto(data_selecionada)
    if not aberto:
        return jsonify({
            "data": data_selecionada,
            "aberto": False,
            "mensagem": "A barbearia não abre neste dia da semana.",
            "horarios": []
        })

    horarios = database.gerar_grade_horarios(data_selecionada)
    return jsonify({
        "data": data_selecionada,
        "aberto": True,
        "horarios": horarios
    })

@app.route("/agendar", methods=["POST"])
def agendar():
    # Suporta requisições JSON e formulários HTML normais
    dados = request.get_json(silent=True) or request.form

    cliente = (dados.get("cliente") or "").strip()
    telefone = (dados.get("telefone") or "").strip()
    data_agenda = (dados.get("data") or "").strip()
    horario = (dados.get("horario") or "").strip()
    servico_id = dados.get("servico_id") or dados.get("servico")
    observacoes = (dados.get("observacoes") or "").strip()

    # Validação do Nome
    if not cliente or len(cliente) < 2:
        erro = "Por favor, informe seu nome completo."
        if request.is_json:
            return jsonify({"erro": erro}), 400
        flash(erro, "danger")
        return redirect(url_for("index"))

    # Validação do Telefone
    telefone_limpo = re.sub(r"\D", "", telefone)
    if len(telefone_limpo) < 10:
        erro = "Por favor, informe um número de WhatsApp válido com DDD."
        if request.is_json:
            return jsonify({"erro": erro}), 400
        flash(erro, "danger")
        return redirect(url_for("index"))

    # Validação de Data
    try:
        dt_agendamento = datetime.datetime.strptime(data_agenda, "%Y-%m-%d").date()
        if dt_agendamento < datetime.date.today():
            erro = "Não é possível agendar em datas que já passaram."
            if request.is_json:
                return jsonify({"erro": erro}), 400
            flash(erro, "danger")
            return redirect(url_for("index"))

        if not database.dia_da_semana_aberto(data_agenda):
            erro = "A Barbearia Arte de Favela atende exclusivamente às Sextas-feiras e aos Sábados."
            if request.is_json:
                return jsonify({"erro": erro}), 400
            flash(erro, "danger")
            return redirect(url_for("index"))
    except Exception:
        erro = "Data selecionada inválida."
        if request.is_json:
            return jsonify({"erro": erro}), 400
        flash(erro, "danger")
        return redirect(url_for("index"))

    # Validação do Serviço
    if not servico_id:
        # Se veio pela API legada sem serviço especificado, atribui o primeiro serviço ativo
        servicos = database.listar_servicos(apenas_ativos=True)
        if servicos:
            servico_id = servicos[0]["id"]
        else:
            erro = "Nenhum serviço disponível no momento."
            if request.is_json:
                return jsonify({"erro": erro}), 400
            flash(erro, "danger")
            return redirect(url_for("index"))

    # Criação do Agendamento com validação atômica de concorrência
    sucesso, mensagem, novo_id = database.criar_novo_agendamento(
        cliente_nome=cliente,
        telefone=telefone,
        servico_id=servico_id,
        data=data_agenda,
        horario=horario,
        observacoes=observacoes,
        status="Agendado"
    )

    if not sucesso:
        if request.is_json:
            return jsonify({"erro": mensagem}), 409
        flash(mensagem, "danger")
        return redirect(url_for("index"))

    if request.is_json:
        return jsonify({
            "mensagem": mensagem,
            "agendamento_id": novo_id
        }), 201

    return redirect(url_for("confirmacao_view", agendamento_id=novo_id))

@app.route("/confirmacao/<int:agendamento_id>")
def confirmacao_view(agendamento_id):
    agendamento = database.obter_agendamento_por_id(agendamento_id)
    if not agendamento:
        flash("Agendamento não localizado.", "danger")
        return redirect(url_for("index"))

    configs = database.obter_todas_configuracoes()

    # Formatar telefone da barbearia para o link wa.me (apenas dígitos)
    whats_barbearia = re.sub(r"\D", "", configs.get("telefone_whatsapp", "11999999999"))
    if not whats_barbearia.startswith("55"):
        whats_barbearia = "55" + whats_barbearia

    # Mensagem pré-formatada para o cliente enviar no WhatsApp se desejar
    msg_whats = (
        f"Olá, Barbearia Arte de Favela! Confirmo meu agendamento:\n"
        f"👤 *Cliente:* {agendamento['cliente']}\n"
        f"✂️ *Serviço:* {agendamento['servico_nome']}\n"
        f"📅 *Data:* {agendamento['data']} às {agendamento['horario']}\n"
        f"💰 *Valor:* R$ {agendamento['valor']:.2f}"
    )

    # Link do Google Calendar
    try:
        dt_start = datetime.datetime.strptime(f"{agendamento['data']} {agendamento['horario']}", "%Y-%m-%d %H:%M")
        duracao = agendamento.get("duracao_minutos") or 30
        dt_end = dt_start + datetime.timedelta(minutes=duracao)
        gcal_dates = f"{dt_start.strftime('%Y%m%dT%H%M%S')}/{dt_end.strftime('%Y%m%dT%H%M%S')}"
    except Exception:
        gcal_dates = ""

    return render_template(
        "confirmacao.html",
        agendamento=agendamento,
        configs=configs,
        whats_link=f"https://wa.me/{whats_barbearia}?text={msg_whats}",
        gcal_dates=gcal_dates
    )

# Rota compatível para listagem direta de agendamentos (Protegida)
@app.route("/agendamentos", methods=["GET"])
@login_required
def listar_agendamentos():
    conexao = database.conectar_banco()
    agendamentos = conexao.execute(
        "SELECT * FROM agendamentos ORDER BY data, horario"
    ).fetchall()
    conexao.close()

    lista = []
    for agendamento in agendamentos:
        lista.append({
            "id": agendamento["id"],
            "cliente": agendamento["cliente"],
            "telefone": agendamento["telefone"],
            "data": agendamento["data"],
            "horario": agendamento["horario"],
            "status": agendamento["status"] if "status" in agendamento.keys() else "Agendado",
            "valor": agendamento["valor"] if "valor" in agendamento.keys() else 35.0,
            "servico": agendamento["servico_nome"] if "servico_nome" in agendamento.keys() else "Corte"
        })

    return jsonify(lista)

# ==============================================================================
# AUTENTICAÇÃO (ADMINISTRADOR / BARBEIRO)
# ==============================================================================

@app.route("/login", methods=["GET", "POST"])
def login_view():
    if request.method == "GET":
        if "usuario_id" in session:
            return redirect(url_for("admin_dashboard"))
        return render_template("login.html")

    # Suporta JSON e Form
    dados = request.get_json(silent=True) or request.form
    nome = (dados.get("nome") or "").strip()
    senha = (dados.get("senha") or "").strip()

    conexao = database.conectar_banco()
    usuario = conexao.execute("SELECT * FROM usuarios WHERE nome = ?", (nome,)).fetchone()
    conexao.close()

    # Validação segura com hash ou fallback temporário para texto puro caso migrado
    valido = False
    if usuario:
        hash_armazenado = usuario["senha"]
        if hash_armazenado.startswith("pbkdf2:") or hash_armazenado.startswith("scrypt:"):
            valido = check_password_hash(hash_armazenado, senha)
        else:
            valido = (hash_armazenado == senha)
            if valido:
                # Atualizar para hash moderno
                novo_hash = generate_password_hash(senha)
                con = database.conectar_banco()
                con.execute("UPDATE usuarios SET senha = ? WHERE id = ?", (novo_hash, usuario["id"]))
                con.commit()
                con.close()

    if valido:
        session["usuario_id"] = usuario["id"]
        session["usuario_nome"] = usuario["nome"]
        session["usuario_tipo"] = usuario["tipo"]

        if request.is_json:
            return jsonify({"mensagem": "Login realizado com sucesso!"})

        flash(f"Bem-vindo de volta, {usuario['nome']}!", "success")
        return redirect(url_for("admin_dashboard"))

    if request.is_json:
        return jsonify({"erro": "Nome ou senha incorretos."}), 401

    flash("Nome ou senha incorretos.", "danger")
    return render_template("login.html", nome=nome)

@app.route("/cadastro", methods=["POST"])
def cadastro():
    dados = request.get_json(silent=True) or request.form
    nome = (dados.get("nome") or "").strip()
    senha = (dados.get("senha") or "").strip()

    if not nome or not senha:
        erro = "Nome e senha são obrigatórios."
        if request.is_json:
            return jsonify({"erro": erro}), 400
        flash(erro, "danger")
        return redirect(url_for("login_view"))

    senha_hash = generate_password_hash(senha)
    conexao = database.conectar_banco()
    try:
        conexao.execute(
            "INSERT INTO usuarios (nome, senha, tipo) VALUES (?, ?, 'admin')",
            (nome, senha_hash)
        )
        conexao.commit()
    except Exception:
        conexao.close()
        erro = "Usuário já existe ou erro ao cadastrar."
        if request.is_json:
            return jsonify({"erro": erro}), 400
        flash(erro, "danger")
        return redirect(url_for("login_view"))

    conexao.close()
    if request.is_json:
        return jsonify({"mensagem": "Usuário cadastrado com sucesso!"}), 201

    flash("Usuário cadastrado com sucesso! Faça login.", "success")
    return redirect(url_for("login_view"))

@app.route("/logout")
def logout_view():
    session.clear()
    flash("Sessão encerrada com sucesso.", "info")
    return redirect(url_for("login_view"))

# ==============================================================================
# PAINEL DO ADMINISTRADOR / BARBEIRO (PROTEGIDO)
# ==============================================================================

@app.route("/admin")
@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    stats = database.obter_estatisticas_dashboard()
    hoje = datetime.date.today().strftime("%Y-%m-%d")
    agendamentos_hoje = database.listar_agendamentos_agenda(filtro="hoje")
    agendamentos_proximos = database.listar_agendamentos_agenda(filtro="proximos")
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        agendamentos_hoje=agendamentos_hoje,
        agendamentos_proximos=agendamentos_proximos,
        hoje=hoje
    )

@app.route("/admin/agenda")
@login_required
def admin_agenda():
    filtro = request.args.get("filtro", "proximos")
    data_especifica = request.args.get("data")
    agendamentos = database.listar_agendamentos_agenda(filtro=filtro, data_especifica=data_especifica)
    servicos = database.listar_servicos(apenas_ativos=True)
    hoje = datetime.date.today().strftime("%Y-%m-%d")

    return render_template(
        "admin/agenda.html",
        agendamentos=agendamentos,
        filtro=filtro,
        data_especifica=data_especifica or hoje,
        servicos=servicos,
        hoje=hoje
    )

@app.route("/api/admin/agendamentos-recentes")
@login_required
def api_admin_agendamentos_recentes():
    proximos = database.listar_agendamentos_agenda(filtro="proximos")
    return jsonify({
        "total": len(proximos),
        "agendamentos": proximos
    })

@app.route("/api/admin/dashboard-stats")
@login_required
def api_admin_dashboard_stats():
    stats = database.obter_estatisticas_dashboard()
    proximos = database.listar_agendamentos_agenda(filtro="proximos")
    return jsonify({
        "stats": stats,
        "total": len(proximos),
        "agendamentos": proximos
    })

@app.route("/admin/agendamento/status", methods=["POST"])
@login_required
def admin_agendamento_status():
    agendamento_id = request.form.get("agendamento_id")
    novo_status = request.form.get("status")

    if novo_status not in ["Agendado", "Confirmado", "Concluído", "Cancelado"]:
        flash("Status inválido.", "danger")
        return redirect(request.referrer or url_for("admin_agenda"))

    database.atualizar_status_agendamento(agendamento_id, novo_status)
    flash(f"Status do agendamento atualizado para '{novo_status}'.", "success")
    return redirect(request.referrer or url_for("admin_agenda"))

@app.route("/admin/agendamento/novo", methods=["POST"])
@login_required
def admin_agendamento_novo():
    cliente = request.form.get("cliente", "").strip()
    telefone = request.form.get("telefone", "").strip()
    data_agenda = request.form.get("data", "").strip()
    horario = request.form.get("horario", "").strip()
    servico_id = request.form.get("servico_id")
    status = request.form.get("status", "Confirmado")
    observacoes = request.form.get("observacoes", "").strip()

    sucesso, msg, _ = database.criar_novo_agendamento(
        cliente_nome=cliente,
        telefone=telefone,
        servico_id=servico_id,
        data=data_agenda,
        horario=horario,
        observacoes=observacoes,
        status=status
    )

    if sucesso:
        flash(f"Agendamento de {cliente} cadastrado com sucesso!", "success")
    else:
        flash(f"Não foi possível agendar: {msg}", "danger")

    return redirect(request.referrer or url_for("admin_agenda"))

@app.route("/admin/agendamento/excluir", methods=["POST"])
@login_required
def admin_agendamento_excluir():
    agendamento_id = request.form.get("agendamento_id")
    database.excluir_agendamento(agendamento_id)
    flash("Agendamento excluído do sistema.", "info")
    return redirect(request.referrer or url_for("admin_agenda"))

@app.route("/admin/faturamento")
@login_required
def admin_faturamento():
    data_param = request.args.get("data")
    dados = database.obter_dados_faturamento(data_especifica=data_param)
    return render_template("admin/faturamento.html", dados=dados)

@app.route("/api/admin/faturamento-dados")
@login_required
def api_admin_faturamento_dados():
    data_param = request.args.get("data")
    dados = database.obter_dados_faturamento(data_especifica=data_param)
    return jsonify(dados)

@app.route("/admin/clientes")
@login_required
def admin_clientes():
    clientes = database.listar_clientes_detalhado()
    return render_template("admin/clientes.html", clientes=clientes)

@app.route("/admin/config")
@login_required
def admin_config():
    configs = database.obter_todas_configuracoes()
    servicos = database.listar_servicos(apenas_ativos=False)
    bloqueios = database.listar_bloqueios_futuros()
    hoje = datetime.date.today().strftime("%Y-%m-%d")

    # Converter lista de dias para lista de inteiros
    dias_ativos = [int(d) for d in configs.get("dias_funcionamento", "1,2,3,4,5,6").split(",") if d]

    return render_template(
        "admin/config.html",
        configs=configs,
        servicos=servicos,
        bloqueios=bloqueios,
        dias_ativos=dias_ativos,
        hoje=hoje
    )

@app.route("/admin/config/horarios", methods=["POST"])
@login_required
def admin_config_horarios():
    database.salvar_configuracao("horario_abertura", request.form.get("horario_abertura", "08:00"))
    database.salvar_configuracao("horario_fechamento", request.form.get("horario_fechamento", "19:00"))
    database.salvar_configuracao("intervalo_minutos", request.form.get("intervalo_minutos", "30"))

    dias_selecionados = request.form.getlist("dias_funcionamento")
    database.salvar_configuracao("dias_funcionamento", ",".join(dias_selecionados))

    database.salvar_configuracao("nome_barbearia", request.form.get("nome_barbearia", "Arte de Favela"))
    database.salvar_configuracao("telefone_whatsapp", request.form.get("telefone_whatsapp", "(11) 99999-9999"))
    database.salvar_configuracao("endereco", request.form.get("endereco", "Rua da Barbearia, 100"))

    flash("Configurações salvas com sucesso!", "success")
    return redirect(url_for("admin_config"))

@app.route("/admin/config/servico/salvar", methods=["POST"])
@login_required
def admin_config_servico_salvar():
    servico_id = request.form.get("servico_id")
    nome = request.form.get("nome", "").strip()
    descricao = request.form.get("descricao", "").strip()
    preco = request.form.get("preco", "0").replace(",", ".")
    duracao = request.form.get("duracao", "30")

    database.salvar_servico(nome, descricao, preco, duracao, servico_id)
    flash(f"Serviço '{nome}' salvo com sucesso!", "success")
    return redirect(url_for("admin_config"))

@app.route("/admin/config/servico/toggle", methods=["POST"])
@login_required
def admin_config_servico_toggle():
    servico_id = request.form.get("servico_id")
    database.alternar_ativo_servico(servico_id)
    flash("Status do serviço alterado.", "info")
    return redirect(url_for("admin_config"))

@app.route("/admin/bloqueio/adicionar", methods=["POST"])
@login_required
def admin_bloqueio_adicionar():
    data_bloqueio = request.form.get("data")
    horario = request.form.get("horario")
    motivo = request.form.get("motivo", "Bloqueado pelo Barbeiro")

    database.adicionar_bloqueio(data_bloqueio, horario, motivo)
    flash(f"Horário {horario} do dia {data_bloqueio} bloqueado com sucesso.", "success")
    return redirect(url_for("admin_config"))

@app.route("/admin/bloqueio/remover", methods=["POST"])
@login_required
def admin_bloqueio_remover():
    bloqueio_id = request.form.get("bloqueio_id")
    database.remover_bloqueio(bloqueio_id)
    flash("Bloqueio removido. Horário liberado para agendamentos.", "success")
    return redirect(url_for("admin_config"))

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    porta = int(os.environ.get("PORT", 5000))
    flask_env = os.environ.get("FLASK_ENV", "development").lower()
    debug_mode = os.environ.get("FLASK_DEBUG", "true").lower() == "true" if flask_env != "production" else False
    engine = os.environ.get("SERVER_ENGINE", "flask").lower()

    ip_rede = obter_ip_local()

    print("\n" + "="*65)
    print(" 💈 BARBEARIA ARTE DE FAVELA - WEB SERVER INICIADO")
    print("="*65)
    print(f" • Modo:           {'PRODUÇÃO (Seguro)' if flask_env == 'production' else 'DESENVOLVIMENTO'}")
    print(f" • Motor WSGI:     {engine.upper()}")
    print(f" • Acesso PC Local: http://localhost:{porta} ou http://127.0.0.1:{porta}")
    print(f" • Acesso Celular:  http://{ip_rede}:{porta} (Mesma rede Wi-Fi)")
    print("="*65)
    print(" [i] Pressione CTRL+C no terminal para encerrar o servidor.")
    print("="*65 + "\n")

    if engine == "waitress" or flask_env == "production":
        try:
            from waitress import serve
            print(f"[*] Executando com Waitress WSGI Server em {host}:{porta} (threads=6)...")
            serve(app, host=host, port=porta, threads=6)
        except ImportError:
            print("[!] Waitress não instalado. Executando com servidor padrão Flask...")
            app.run(host=host, port=porta, debug=debug_mode)
    else:
        app.run(host=host, port=porta, debug=debug_mode)

import sqlite3
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

BANCO = "agenda.db"

def conectar_banco():
    conexao = sqlite3.connect(BANCO)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao

def criar_banco():
    conexao = conectar_banco()
    cursor = conexao.cursor()

    # Tabela de Usuários (com permissões e hash de senha)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            tipo TEXT DEFAULT 'admin'
        )
    """)

    # Tabela de Clientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT UNIQUE NOT NULL,
            data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de Serviços
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS servicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            preco REAL NOT NULL,
            duracao_minutos INTEGER DEFAULT 30,
            ativo INTEGER DEFAULT 1
        )
    """)

    # Tabela de Agendamentos (com suporte a status, valor e chave de serviço)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            cliente TEXT NOT NULL,
            telefone TEXT NOT NULL,
            servico_id INTEGER,
            servico_nome TEXT NOT NULL,
            data TEXT NOT NULL,
            horario TEXT NOT NULL,
            valor REAL NOT NULL,
            status TEXT DEFAULT 'Agendado',
            observacoes TEXT,
            criado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (servico_id) REFERENCES servicos(id)
        )
    """)

    # Tabela de Configurações da Barbearia
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    """)

    # Tabela de Bloqueios de Horários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bloqueios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            horario TEXT NOT NULL,
            motivo TEXT
        )
    """)

    conexao.commit()

    # Inserir dados padrão caso ainda não existam
    _seed_dados_iniciais(cursor, conexao)

    conexao.close()

def _seed_dados_iniciais(cursor, conexao):
    # 1. Usuário Administrador (Carlos_Alberto / CarlosAlt2018)
    cursor.execute("DELETE FROM usuarios WHERE nome = 'admin'")
    senha_hash = generate_password_hash("CarlosAlt2018")
    cursor.execute("SELECT id FROM usuarios WHERE nome = 'Carlos_Alberto'")
    user_row = cursor.fetchone()
    if not user_row:
        cursor.execute(
            "INSERT INTO usuarios (nome, senha, tipo) VALUES (?, ?, ?)",
            ("Carlos_Alberto", senha_hash, "admin")
        )
    else:
        cursor.execute(
            "UPDATE usuarios SET senha = ? WHERE nome = 'Carlos_Alberto'",
            (senha_hash,)
        )

    # 2. Serviços Padrão
    cursor.execute("SELECT COUNT(*) as total FROM servicos")
    if cursor.fetchone()["total"] == 0:
        servicos_iniciais = [
            ("Corte de Cabelo", "Corte moderno degradê/social com acabamento impecável. Inclui sobrancelha!", 35.00, 30, 1),
            ("Sobrancelha", "Alinhamento e desenho de sobrancelha na lâmina ou pinça.", 15.00, 15, 1),
            ("Barba", "Barboterapia completa com toalha quente, alinhamento e óleo hidratante.", 30.00, 30, 1),
            ("Combo Arte de Favela", "Corte de Cabelo + Barba completa + Sobrancelha (Experiência VIP).", 55.00, 60, 1)
        ]
        cursor.executemany(
            "INSERT INTO servicos (nome, descricao, preco, duracao_minutos, ativo) VALUES (?, ?, ?, ?, ?)",
            servicos_iniciais
        )

    # 3. Configurações Padrão de Atendimento (Sexta e Sábado: 08:00 às 20:30)
    config_defaults = {
        "horario_abertura": "08:00",
        "horario_fechamento": "20:30",
        "horario_fechamento_sabado": "20:30",
        "intervalo_minutos": "30",
        "dias_funcionamento": "5,6", # 5=Sexta, 6=Sábado
        "nome_barbearia": "Arte de Favela",
        "telefone_whatsapp": "(11) 98510-4901",
        "endereco": "Rua Principal, 123 - Favela Chic"
    }

    for chave, valor in config_defaults.items():
        cursor.execute("INSERT OR IGNORE INTO configuracoes (chave, valor) VALUES (?, ?)", (chave, valor))

    # Garantir horários e dias de funcionamento atualizados (08:00 às 20:30)
    cursor.execute("UPDATE configuracoes SET valor = '08:00' WHERE chave = 'horario_abertura'")
    cursor.execute("UPDATE configuracoes SET valor = '20:30' WHERE chave = 'horario_fechamento'")
    cursor.execute("UPDATE configuracoes SET valor = '20:30' WHERE chave = 'horario_fechamento_sabado'")
    cursor.execute("UPDATE configuracoes SET valor = '5,6' WHERE chave = 'dias_funcionamento'")

    conexao.commit()

# --- Helpers de Configurações ---

def obter_configuracao(chave, valor_padrao=None):
    conexao = conectar_banco()
    res = conexao.execute("SELECT valor FROM configuracoes WHERE chave = ?", (chave,)).fetchone()
    conexao.close()
    return res["valor"] if res else valor_padrao

def salvar_configuracao(chave, valor):
    conexao = conectar_banco()
    conexao.execute(
        "INSERT INTO configuracoes (chave, valor) VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
        (chave, str(valor))
    )
    conexao.commit()
    conexao.close()

def obter_todas_configuracoes():
    conexao = conectar_banco()
    linhas = conexao.execute("SELECT chave, valor FROM configuracoes").fetchall()
    conexao.close()
    return {linha["chave"]: linha["valor"] for linha in linhas}

# --- Helpers de Serviços ---

def listar_servicos(apenas_ativos=True):
    conexao = conectar_banco()
    query = "SELECT * FROM servicos"
    if apenas_ativos:
        query += " WHERE ativo = 1"
    query += " ORDER BY preco ASC"
    servicos = conexao.execute(query).fetchall()
    conexao.close()
    return [dict(s) for s in servicos]

def obter_servico_por_id(servico_id):
    conexao = conectar_banco()
    s = conexao.execute("SELECT * FROM servicos WHERE id = ?", (servico_id,)).fetchone()
    conexao.close()
    return dict(s) if s else None

def salvar_servico(nome, descricao, preco, duracao=30, servico_id=None):
    conexao = conectar_banco()
    if servico_id:
        conexao.execute(
            "UPDATE servicos SET nome = ?, descricao = ?, preco = ?, duracao_minutos = ? WHERE id = ?",
            (nome, descricao, float(preco), int(duracao), int(servico_id))
        )
    else:
        conexao.execute(
            "INSERT INTO servicos (nome, descricao, preco, duracao_minutos, ativo) VALUES (?, ?, ?, ?, 1)",
            (nome, descricao, float(preco), int(duracao))
        )
    conexao.commit()
    conexao.close()

def alternar_ativo_servico(servico_id):
    conexao = conectar_banco()
    servico = conexao.execute("SELECT ativo FROM servicos WHERE id = ?", (servico_id,)).fetchone()
    if servico:
        novo_status = 0 if servico["ativo"] == 1 else 1
        conexao.execute("UPDATE servicos SET ativo = ? WHERE id = ?", (novo_status, servico_id))
        conexao.commit()
    conexao.close()

# --- Gerenciamento de Horários e Disponibilidade ---

def dia_da_semana_aberto(data_str):
    try:
        dt = datetime.datetime.strptime(data_str, "%Y-%m-%d")
        # Python weekday: Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6
        # Nosso padrão configurado: 1=Segunda, 2=Terça, ..., 5=Sexta, 6=Sábado, 0=Domingo
        dia_semana_config = (dt.weekday() + 1) % 7
        dias_abertos = [int(d.strip()) for d in obter_configuracao("dias_funcionamento", "5,6").split(",") if d.strip()]
        return dia_semana_config in dias_abertos
    except Exception:
        return False

def gerar_grade_horarios(data_str):
    """
    Gera todos os horários entre abertura e fechamento para a data indicada,
    indicando status: disponível, ocupado, almoço ou bloqueado.
    """
    if not dia_da_semana_aberto(data_str):
        return []

    dt = datetime.datetime.strptime(data_str, "%Y-%m-%d")
    dia_semana_config = (dt.weekday() + 1) % 7

    abertura_str = obter_configuracao("horario_abertura", "08:00")
    # Sexta-feira e Sábado: 08:00 às 20:30
    if dia_semana_config == 6:
        fechamento_str = obter_configuracao("horario_fechamento_sabado", "20:30")
    else:
        fechamento_str = obter_configuracao("horario_fechamento", "20:30")

    intervalo_min = int(obter_configuracao("intervalo_minutos", "30"))

    fmt = "%H:%M"
    hora_atual = datetime.datetime.strptime(abertura_str, fmt)
    hora_fim = datetime.datetime.strptime(fechamento_str, fmt)

    conexao = conectar_banco()

    # Horários ocupados por agendamentos (não cancelados)
    agendamentos = conexao.execute(
        "SELECT horario FROM agendamentos WHERE data = ? AND status != 'Cancelado'",
        (data_str,)
    ).fetchall()
    horarios_ocupados = set(a["horario"] for a in agendamentos)

    # Horários bloqueados pelo barbeiro
    bloqueios = conexao.execute(
        "SELECT horario, motivo FROM bloqueios WHERE data = ?",
        (data_str,)
    ).fetchall()
    bloqueios_map = {b["horario"]: (b["motivo"] or "Bloqueado pelo barbeiro") for b in bloqueios}

    conexao.close()

    # Se a data for hoje, verificar horários que já passaram
    hoje_str = datetime.date.today().strftime("%Y-%m-%d")
    agora = datetime.datetime.now()

    grade = []
    while hora_atual < hora_fim:
        slot_str = hora_atual.strftime(fmt)
        slot_time = hora_atual.time()

        # Intervalo de Almoço das 13:00 até às 14:00 (13:00, 13:30 e 14:00)
        is_almoco = datetime.time(13, 0) <= slot_time <= datetime.time(14, 0)

        is_passado = False
        if data_str < hoje_str:
            is_passado = True
        elif data_str == hoje_str:
            if slot_time <= agora.time():
                is_passado = True

        if is_passado:
            disponivel = False
            status_desc = "Horário já passou"
            tipo_status = "passado"
        elif is_almoco:
            disponivel = False
            status_desc = "Horário de Almoço (13:00 às 14:00)"
            tipo_status = "almoco"
        elif slot_str in bloqueios_map:
            disponivel = False
            status_desc = bloqueios_map[slot_str]
            tipo_status = "bloqueado"
        elif slot_str in horarios_ocupados:
            disponivel = False
            status_desc = "Ocupado"
            tipo_status = "ocupado"
        else:
            disponivel = True
            status_desc = "Disponível"
            tipo_status = "disponivel"

        grade.append({
            "horario": slot_str,
            "disponivel": disponivel,
            "status": status_desc,
            "tipo": tipo_status
        })

        hora_atual += datetime.timedelta(minutes=intervalo_min)

    return grade

def verificar_horario_livre(data_str, horario_str, ignorar_agendamento_id=None):
    # 1. Valida se o horário está no intervalo de almoço (13:00 às 14:00)
    try:
        hora_val = datetime.datetime.strptime(horario_str.strip(), "%H:%M").time()
        if datetime.time(13, 0) <= hora_val <= datetime.time(14, 0):
            return False, "Horário de almoço da barbearia (13:00 às 14:00). Escolha outro horário para atendimento."
    except Exception:
        pass

    conexao = conectar_banco()

    # 2. Verifica bloqueio manual do barbeiro
    bloqueado = conexao.execute(
        "SELECT 1 FROM bloqueios WHERE data = ? AND horario = ?",
        (data_str, horario_str)
    ).fetchone()

    if bloqueado:
        conexao.close()
        return False, "Esse horário está bloqueado pelo barbeiro."

    # 3. Verifica agendamento conflitante
    query = "SELECT 1 FROM agendamentos WHERE data = ? AND horario = ? AND status != 'Cancelado'"
    params = [data_str, horario_str]
    if ignorar_agendamento_id:
        query += " AND id != ?"
        params.append(ignorar_agendamento_id)

    existente = conexao.execute(query, tuple(params)).fetchone()
    conexao.close()

    if existente:
        return False, "Esse horário já está ocupado."

    return True, "Horário disponível."

# --- Gerenciamento de Clientes e Agendamentos ---

def obter_ou_criar_cliente(nome, telefone):
    conexao = conectar_banco()
    cliente = conexao.execute("SELECT * FROM clientes WHERE telefone = ?", (telefone,)).fetchone()
    if cliente:
        # Atualiza nome se necessário
        if cliente["nome"] != nome:
            conexao.execute("UPDATE clientes SET nome = ? WHERE id = ?", (nome, cliente["id"]))
            conexao.commit()
        cliente_id = cliente["id"]
    else:
        cursor = conexao.execute("INSERT INTO clientes (nome, telefone) VALUES (?, ?)", (nome, telefone))
        conexao.commit()
        cliente_id = cursor.lastrowid
    conexao.close()
    return cliente_id

def criar_novo_agendamento(cliente_nome, telefone, servico_id, data, horario, observacoes="", status="Agendado"):
    livre, motivo = verificar_horario_livre(data, horario)
    if not livre:
        return False, motivo, None

    servico = obter_servico_por_id(servico_id)
    if not servico:
        return False, "Serviço inválido ou não encontrado.", None

    cliente_id = obter_ou_criar_cliente(cliente_nome, telefone)

    conexao = conectar_banco()
    cursor = conexao.execute(
        """
        INSERT INTO agendamentos
        (cliente_id, cliente, telefone, servico_id, servico_nome, data, horario, valor, status, observacoes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (cliente_id, cliente_nome, telefone, servico_id, servico["nome"], data, horario, servico["preco"], status, observacoes)
    )
    novo_id = cursor.lastrowid
    conexao.commit()
    conexao.close()

    return True, "Agendamento realizado com sucesso!", novo_id

def obter_agendamento_por_id(agendamento_id):
    conexao = conectar_banco()
    row = conexao.execute("""
        SELECT a.*, s.descricao as servico_descricao, s.duracao_minutos
        FROM agendamentos a
        LEFT JOIN servicos s ON a.servico_id = s.id
        WHERE a.id = ?
    """, (agendamento_id,)).fetchone()
    conexao.close()
    return dict(row) if row else None

def atualizar_status_agendamento(agendamento_id, novo_status):
    conexao = conectar_banco()
    conexao.execute("UPDATE agendamentos SET status = ? WHERE id = ?", (novo_status, agendamento_id))
    conexao.commit()
    conexao.close()

def excluir_agendamento(agendamento_id):
    conexao = conectar_banco()
    conexao.execute("DELETE FROM agendamentos WHERE id = ?", (agendamento_id,))
    conexao.commit()
    conexao.close()

def adicionar_bloqueio(data, horario, motivo):
    conexao = conectar_banco()
    conexao.execute(
        "INSERT INTO bloqueios (data, horario, motivo) VALUES (?, ?, ?)",
        (data, horario, motivo)
    )
    conexao.commit()
    conexao.close()

def remover_bloqueio(bloqueio_id):
    conexao = conectar_banco()
    conexao.execute("DELETE FROM bloqueios WHERE id = ?", (bloqueio_id,))
    conexao.commit()
    conexao.close()

def listar_bloqueios_futuros():
    hoje = datetime.date.today().strftime("%Y-%m-%d")
    conexao = conectar_banco()
    rows = conexao.execute(
        "SELECT * FROM bloqueios WHERE data >= ? ORDER BY data ASC, horario ASC",
        (hoje,)
    ).fetchall()
    conexao.close()
    return [dict(r) for r in rows]

# --- Consultas para o Painel do Barbeiro / Relatórios ---

def listar_agendamentos_agenda(filtro="hoje", data_especifica=None):
    hoje = datetime.date.today()
    hoje_str = hoje.strftime("%Y-%m-%d")
    amanha_str = (hoje + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    # Início e fim da semana (Segunda a Domingo)
    inicio_semana = hoje - datetime.timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + datetime.timedelta(days=6)
    inicio_semana_str = inicio_semana.strftime("%Y-%m-%d")
    fim_semana_str = fim_semana.strftime("%Y-%m-%d")

    # Início e fim do mês
    inicio_mes_str = hoje.strftime("%Y-%m-01")
    proximo_mes = (hoje.replace(day=28) + datetime.timedelta(days=4))
    fim_mes_str = (proximo_mes - datetime.timedelta(days=proximo_mes.day)).strftime("%Y-%m-%d")

    query = "SELECT * FROM agendamentos WHERE 1=1"
    params = []

    if filtro == "proximos" or not filtro:
        query += " AND data >= ? AND status != 'Cancelado'"
        params.append(hoje_str)
    elif filtro == "hoje":
        query += " AND data = ?"
        params.append(hoje_str)
    elif filtro == "amanha":
        query += " AND data = ?"
        params.append(amanha_str)
    elif filtro == "semana":
        query += " AND data BETWEEN ? AND ?"
        params.extend([inicio_semana_str, fim_semana_str])
    elif filtro == "mes":
        query += " AND data BETWEEN ? AND ?"
        params.extend([inicio_mes_str, fim_mes_str])
    elif filtro == "sexta":
        query += " AND strftime('%w', data) = '5' AND data >= ?"
        params.append(hoje_str)
    elif filtro == "sabado":
        query += " AND strftime('%w', data) = '6' AND data >= ?"
        params.append(hoje_str)
    elif filtro == "todos":
        pass
    elif filtro == "data" and data_especifica:
        query += " AND data = ?"
        params.append(data_especifica)

    query += " ORDER BY data ASC, horario ASC"

    conexao = conectar_banco()
    rows = conexao.execute(query, tuple(params)).fetchall()
    conexao.close()
    return [dict(r) for r in rows]

def obter_estatisticas_dashboard():
    hoje = datetime.date.today()
    hoje_str = hoje.strftime("%Y-%m-%d")
    inicio_mes_str = hoje.strftime("%Y-%m-01")

    # Início e fim da semana (Segunda a Domingo)
    inicio_semana = (hoje - datetime.timedelta(days=hoje.weekday())).strftime("%Y-%m-%d")
    fim_semana = (hoje - datetime.timedelta(days=hoje.weekday()) + datetime.timedelta(days=6)).strftime("%Y-%m-%d")

    # Fim do mês atual
    if hoje.month == 12:
        fim_mes_str = f"{hoje.year}-12-31"
    else:
        prox_mes = datetime.date(hoje.year, hoje.month + 1, 1)
        fim_mes_str = (prox_mes - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    conexao = conectar_banco()

    # Agendamentos de hoje
    agendamentos_hoje = conexao.execute(
        "SELECT COUNT(*) as total FROM agendamentos WHERE data = ? AND status != 'Cancelado'",
        (hoje_str,)
    ).fetchone()["total"]

    # Próximos agendamentos (a partir de hoje não cancelados)
    proximos_agendamentos = conexao.execute(
        """
        SELECT * FROM agendamentos
        WHERE data >= ? AND status != 'Cancelado'
        ORDER BY data ASC, horario ASC
        LIMIT 20
        """,
        (hoje_str,)
    ).fetchall()

    # Total de clientes cadastrados
    total_clientes = conexao.execute("SELECT COUNT(*) as total FROM clientes").fetchone()["total"]

    # Total de agendamentos ativos
    total_agendamentos_ativos = conexao.execute(
        "SELECT COUNT(*) as total FROM agendamentos WHERE status != 'Cancelado'"
    ).fetchone()["total"]

    # Faturamento de hoje (atualizado imediatamente com cada agendamento)
    faturamento_hoje = conexao.execute(
        "SELECT COALESCE(SUM(valor), 0) as total FROM agendamentos WHERE data = ? AND status != 'Cancelado'",
        (hoje_str,)
    ).fetchone()["total"]

    # Faturamento da semana (a partir do início da semana)
    faturamento_semana = conexao.execute(
        "SELECT COALESCE(SUM(valor), 0) as total FROM agendamentos WHERE data >= ? AND status != 'Cancelado'",
        (inicio_semana,)
    ).fetchone()["total"]

    # Faturamento do mês (atualizado imediatamente com cada agendamento a partir do início do mês)
    faturamento_mes = conexao.execute(
        "SELECT COALESCE(SUM(valor), 0) as total FROM agendamentos WHERE data >= ? AND status != 'Cancelado'",
        (inicio_mes_str,)
    ).fetchone()["total"]

    # Faturamento total confirmado de todos os agendamentos ativos
    faturamento_total_confirmado = conexao.execute(
        "SELECT COALESCE(SUM(valor), 0) as total FROM agendamentos WHERE status != 'Cancelado'"
    ).fetchone()["total"]

    conexao.close()

    return {
        "agendamentos_hoje": agendamentos_hoje,
        "proximos_agendamentos": [dict(p) for p in proximos_agendamentos],
        "total_clientes": total_clientes,
        "total_agendamentos_ativos": total_agendamentos_ativos,
        "faturamento_hoje": float(faturamento_hoje),
        "faturamento_semana": float(faturamento_semana),
        "faturamento_mes": float(faturamento_mes),
        "faturamento_total_confirmado": float(faturamento_total_confirmado)
    }

def obter_dados_faturamento(data_especifica=None):
    hoje = datetime.date.today()
    hoje_str = hoje.strftime("%Y-%m-%d")
    data_sel = data_especifica if data_especifica else hoje_str

    # Início da semana (Segunda-feira)
    inicio_semana = (hoje - datetime.timedelta(days=hoje.weekday())).strftime("%Y-%m-%d")

    # Início do mês
    inicio_mes = hoje.strftime("%Y-%m-01")

    conexao = conectar_banco()

    # Faturamentos atualizados imediatamente com os agendamentos marcados (status != 'Cancelado')
    fat_hoje = conexao.execute(
        "SELECT COALESCE(SUM(valor), 0) as total FROM agendamentos WHERE data = ? AND status != 'Cancelado'",
        (hoje_str,)
    ).fetchone()["total"]

    fat_semana = conexao.execute(
        "SELECT COALESCE(SUM(valor), 0) as total FROM agendamentos WHERE data >= ? AND status != 'Cancelado'",
        (inicio_semana,)
    ).fetchone()["total"]

    fat_mes = conexao.execute(
        "SELECT COALESCE(SUM(valor), 0) as total FROM agendamentos WHERE data >= ? AND status != 'Cancelado'",
        (inicio_mes,)
    ).fetchone()["total"]

    fat_total_geral = conexao.execute(
        "SELECT COALESCE(SUM(valor), 0) as total FROM agendamentos WHERE status != 'Cancelado'"
    ).fetchone()["total"]

    fat_dia_selecionado = conexao.execute(
        "SELECT COALESCE(SUM(valor), 0) as total FROM agendamentos WHERE data = ? AND status != 'Cancelado'",
        (data_sel,)
    ).fetchone()["total"]

    total_concluidos_mes = conexao.execute(
        "SELECT COUNT(*) as total FROM agendamentos WHERE data >= ? AND status != 'Cancelado'",
        (inicio_mes,)
    ).fetchone()["total"]

    total_agendamentos_dia_selecionado = conexao.execute(
        "SELECT COUNT(*) as total FROM agendamentos WHERE data = ? AND status != 'Cancelado'",
        (data_sel,)
    ).fetchone()["total"]

    # Quantidade por tipo de serviço no mês (Atualizado com todos os agendamentos ativos)
    servicos_stats = conexao.execute(
        """
        SELECT servico_nome, COUNT(*) as qtd, COALESCE(SUM(valor), 0) as total_valor
        FROM agendamentos
        WHERE data >= ? AND status != 'Cancelado'
        GROUP BY servico_nome
        ORDER BY qtd DESC
        """,
        (inicio_mes,)
    ).fetchall()

    # 1. Evolução dos últimos 7 dias (histórico até hoje)
    ultimos_7_dias = []
    for i in range(6, -1, -1):
        dia_ref = hoje - datetime.timedelta(days=i)
        dia_str = dia_ref.strftime("%Y-%m-%d")
        label = dia_ref.strftime("%d/%m")
        res = conexao.execute(
            "SELECT COALESCE(SUM(valor), 0) as total, COUNT(*) as qtd FROM agendamentos WHERE data = ? AND status != 'Cancelado'",
            (dia_str,)
        ).fetchone()
        ultimos_7_dias.append({
            "data": dia_str,
            "label": label,
            "valor": float(res["total"]),
            "qtd": int(res["qtd"])
        })

    # 2. Evolução de Hoje + Próximos 7 dias (agendamentos futuros marcados)
    proximos_7_dias = []
    for i in range(0, 7):
        dia_ref = hoje + datetime.timedelta(days=i)
        dia_str = dia_ref.strftime("%Y-%m-%d")
        label = dia_ref.strftime("%d/%m")
        res = conexao.execute(
            "SELECT COALESCE(SUM(valor), 0) as total, COUNT(*) as qtd FROM agendamentos WHERE data = ? AND status != 'Cancelado'",
            (dia_str,)
        ).fetchone()
        proximos_7_dias.append({
            "data": dia_str,
            "label": label,
            "valor": float(res["total"]),
            "qtd": int(res["qtd"])
        })

    # 3. Faturamento por Horário Marcado no DIA SELECIONADO
    abertura_str = obter_configuracao("horario_abertura", "08:00")
    fechamento_str = obter_configuracao("horario_fechamento", "20:30")
    intervalo_min = int(obter_configuracao("intervalo_minutos", "30"))

    horarios_dia_rows = conexao.execute(
        """
        SELECT horario, COUNT(*) as qtd, COALESCE(SUM(valor), 0) as total_valor,
               GROUP_CONCAT(cliente || ' (' || servico_nome || ' - R$ ' || printf('%.2f', valor) || ')', ' | ') as clientes_servicos
        FROM agendamentos
        WHERE data = ? AND status != 'Cancelado'
        GROUP BY horario
        ORDER BY horario ASC
        """,
        (data_sel,)
    ).fetchall()
    horarios_dia_map = {r["horario"]: r for r in horarios_dia_rows}

    # Grade padrão de horários da barbearia (excluindo almoço 13:00-14:00)
    fmt = "%H:%M"
    hora_cursor = datetime.datetime.strptime(abertura_str, fmt)
    hora_limite = datetime.datetime.strptime(fechamento_str, fmt)
    grade_horarios_dia = []

    while hora_cursor < hora_limite:
        slot_s = hora_cursor.strftime(fmt)
        is_almoco = datetime.time(13, 0) <= hora_cursor.time() <= datetime.time(14, 0)
        if not is_almoco:
            if slot_s in horarios_dia_map:
                r = horarios_dia_map[slot_s]
                grade_horarios_dia.append({
                    "horario": slot_s,
                    "qtd": int(r["qtd"]),
                    "valor": float(r["total_valor"]),
                    "detalhes": r["clientes_servicos"] or ""
                })
            else:
                grade_horarios_dia.append({
                    "horario": slot_s,
                    "qtd": 0,
                    "valor": 0.0,
                    "detalhes": "Sem agendamentos neste horário"
                })
        hora_cursor += datetime.timedelta(minutes=intervalo_min)

    # 4. Faturamento Geral por Horário Marcado (distribuição acumulada de receita por horário)
    horarios_geral_rows = conexao.execute(
        """
        SELECT horario, COUNT(*) as qtd, COALESCE(SUM(valor), 0) as total_valor
        FROM agendamentos
        WHERE status != 'Cancelado'
        GROUP BY horario
        ORDER BY horario ASC
        """
    ).fetchall()
    
    grafico_horarios_geral = [
        {
            "horario": r["horario"],
            "qtd": int(r["qtd"]),
            "valor": float(r["total_valor"])
        }
        for r in horarios_geral_rows
    ]

    # 5. Lista de dias com agendamentos ativos cadastrados (para busca rápida)
    dias_ativos_rows = conexao.execute(
        """
        SELECT DISTINCT data, COUNT(*) as qtd, COALESCE(SUM(valor), 0) as total_dia
        FROM agendamentos
        WHERE status != 'Cancelado'
        GROUP BY data
        ORDER BY data DESC
        LIMIT 30
        """
    ).fetchall()
    dias_com_agendamentos = [
        {"data": r["data"], "qtd": r["qtd"], "total": float(r["total_dia"])}
        for r in dias_ativos_rows
    ]

    # 6. Agendamentos detalhados do dia selecionado
    agendamentos_dia = conexao.execute(
        """
        SELECT id, cliente, telefone, horario, servico_nome, valor, status
        FROM agendamentos
        WHERE data = ? AND status != 'Cancelado'
        ORDER BY horario ASC
        """,
        (data_sel,)
    ).fetchall()

    conexao.close()

    return {
        "fat_hoje": float(fat_hoje),
        "fat_semana": float(fat_semana),
        "fat_mes": float(fat_mes),
        "fat_total_geral": float(fat_total_geral),
        "fat_dia_selecionado": float(fat_dia_selecionado),
        "total_agendamentos_dia": total_agendamentos_dia_selecionado,
        "data_selecionada": data_sel,
        "total_concluidos_mes": total_concluidos_mes,
        "servicos_stats": [dict(s) for s in servicos_stats],
        "grafico_7_dias": ultimos_7_dias,
        "grafico_proximos_7_dias": proximos_7_dias,
        "grafico_horarios_dia": grade_horarios_dia,
        "grafico_horarios_geral": grafico_horarios_geral,
        "dias_com_agendamentos": dias_com_agendamentos,
        "agendamentos_dia": [dict(a) for a in agendamentos_dia]
    }

def listar_clientes_detalhado():
    conexao = conectar_banco()
    rows = conexao.execute("""
        SELECT 
            c.id, 
            c.nome, 
            c.telefone, 
            c.data_cadastro,
            COUNT(a.id) as total_agendamentos,
            MAX(a.data) as ultimo_atendimento,
            (
                SELECT servico_nome 
                FROM agendamentos 
                WHERE cliente_id = c.id 
                GROUP BY servico_nome 
                ORDER BY COUNT(*) DESC 
                LIMIT 1
            ) as servico_favorito
        FROM clientes c
        LEFT JOIN agendamentos a ON c.id = a.cliente_id
        GROUP BY c.id
        ORDER BY total_agendamentos DESC, c.nome ASC
    """).fetchall()

    clientes = []
    for r in rows:
        d = dict(r)
        # Obter histórico recente do cliente
        historico = conexao.execute(
            "SELECT data, horario, servico_nome, valor, status FROM agendamentos WHERE cliente_id = ? ORDER BY data DESC, horario DESC LIMIT 5",
            (r["id"],)
        ).fetchall()
        d["historico"] = [dict(h) for h in historico]
        clientes.append(d)

    conexao.close()
    return clientes

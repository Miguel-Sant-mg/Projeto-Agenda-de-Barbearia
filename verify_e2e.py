import urllib.request
import urllib.parse
import json

BASE_URL = "http://127.0.0.1:5000"

def test_e2e():
    print("Iniciando testes E2E via cliente HTTP...")

    # 1. Página inicial
    with urllib.request.urlopen(f"{BASE_URL}/") as resp:
        assert resp.status == 200
        html = resp.read().decode('utf-8')
        assert "Arte de Favela" in html
        assert "Combo Arte de Favela" in html
        assert "Corte de Cabelo" in html
        print("[OK] Pagina inicial carregada com sucesso e servicos listados.")

    # 2. API de Horarios Disponiveis (Sexta-feira aberta)
    data_teste = "2026-10-16"
    with urllib.request.urlopen(f"{BASE_URL}/api/horarios-disponiveis?data={data_teste}") as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode('utf-8'))
        assert data["aberto"] is True
        assert len(data["horarios"]) > 0
        primeiro_horario = data["horarios"][0]["horario"]
        print(f"[OK] API de horarios retornou {len(data['horarios'])} slots para {data_teste}. Primeiro: {primeiro_horario}")

    # 3. Realizar Agendamento (POST /agendar)
    payload = json.dumps({
        "cliente": "Lucas E2E",
        "telefone": "(11) 97777-8888",
        "servico_id": 1,
        "data": data_teste,
        "horario": primeiro_horario,
        "observacoes": "Corte com acabamento especial"
    }).encode('utf-8')

    req = urllib.request.Request(
        f"{BASE_URL}/agendar",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 201
        res_json = json.loads(resp.read().decode('utf-8'))
        novo_id = res_json["agendamento_id"]
        print(f"[OK] Agendamento realizado com sucesso! ID gerado: {novo_id}")

    # 4. Acessar tela de confirmacao do agendamento
    with urllib.request.urlopen(f"{BASE_URL}/confirmacao/{novo_id}") as resp:
        assert resp.status == 200
        conf_html = resp.read().decode('utf-8')
        assert "AGENDAMENTO CONFIRMADO!" in conf_html
        assert "Lucas E2E" in conf_html
        assert primeiro_horario in conf_html
        assert "wa.me" in conf_html
        assert "calendar.google.com" in conf_html
        print("[OK] Tela de confirmacao renderizada perfeitamente com WhatsApp e Google Calendar.")

    # 5. Tentativa de agendamento duplicado (deve rejeitar com 409)
    req_dup = urllib.request.Request(
        f"{BASE_URL}/agendar",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req_dup)
        assert False, "Deveria ter retornado erro 409 Conflito"
    except urllib.error.HTTPError as e:
        assert e.code == 409
        print("[OK] Bloqueio contra agendamento duplicado funcionando (HTTP 409 retornado).")

    # 6. Autenticacao do Administrador
    login_payload = json.dumps({
        "nome": "Carlos_Alberto",
        "senha": "CarlosAlt2018"
    }).encode('utf-8')
    req_login = urllib.request.Request(
        f"{BASE_URL}/login",
        data=login_payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_login) as resp:
        assert resp.status == 200
        print("[OK] Login do administrador validado com sucesso via API.")

    print("\nTODOS OS TESTES E2E FORAM CONCLUIDOS COM 100% DE SUCESSO!")

if __name__ == "__main__":
    test_e2e()

import urllib.request
import urllib.parse
import json
import http.cookiejar

BASE_URL = "http://127.0.0.1:5000"

def test_admin_update():
    print("Testando atualizacao imediata no painel administrativo...")
    
    # 1. Configurar gerenciador de cookies para a sessao do admin
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    # 2. Fazer login como admin
    login_data = urllib.parse.urlencode({"nome": "admin", "senha": "admin123"}).encode('utf-8')
    req_login = urllib.request.Request(f"{BASE_URL}/login", data=login_data)
    with opener.open(req_login) as resp:
        assert resp.status == 200

    # 3. Criar novo agendamento via cliente no site (para Sexta-feira 2026-10-16 as 11:30)
    nome_cliente = "Carlos Eduardo Favela"
    telefone_cliente = "(11) 97711-2233"
    data_marcada = "2026-10-16"
    horario_marcado = "11:30"

    novo_agendamento = json.dumps({
        "cliente": nome_cliente,
        "telefone": telefone_cliente,
        "servico_id": 1,
        "data": data_marcada,
        "horario": horario_marcado,
        "observacoes": "Degrade navalhado na zero"
    }).encode('utf-8')

    req_book = urllib.request.Request(
        f"{BASE_URL}/agendar",
        data=novo_agendamento,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_book) as resp:
        assert resp.status == 201
        res = json.loads(resp.read().decode('utf-8'))
        print(f"[OK] Cliente realizou agendamento com sucesso. ID: {res['agendamento_id']}")

    # 4. Acessar o Dashboard com a sessao autenticada do admin
    with opener.open(f"{BASE_URL}/admin/dashboard") as resp:
        assert resp.status == 200
        html = resp.read().decode('utf-8')
        
        # Verificar se o nome, horario, dia e telefone aparecem na tabela do admin
        assert nome_cliente in html, "Nome do cliente deveria constar no dashboard!"
        assert horario_marcado in html, "Horario deveria constar no dashboard!"
        assert telefone_cliente in html, "Telefone deveria constar no dashboard!"
        assert "Sexta-feira" in html, "Dia da semana deveria constar no dashboard!"
        assert "Dia Marcado" in html, "Coluna Dia Marcado deve estar presente!"
        assert "Número de Telefone / WhatsApp" in html, "Coluna WhatsApp deve estar presente!"
        print(f"[OK] Dashboard exibiu imediatamente: Cliente '{nome_cliente}', Horario '{horario_marcado}h', Telefone '{telefone_cliente}' e Dia Marcado 'Sexta-feira'!")

    # 5. Acessar a API de agendamentos recentes
    with opener.open(f"{BASE_URL}/api/admin/agendamentos-recentes") as resp:
        assert resp.status == 200
        dados_api = json.loads(resp.read().decode('utf-8'))
        assert dados_api["total"] > 0
        encontrado = any(a["cliente"] == nome_cliente and a["horario"] == horario_marcado for a in dados_api["agendamentos"])
        assert encontrado, "Agendamento deve constar na API de agendamentos recentes!"
        print("[OK] API de atualizacao em tempo real retornou o novo agendamento com todos os campos!")

    print("\nTESTE DE ATUALIZACAO DO PAINEL CONCLUIDO COM 100% DE SUCESSO!")

if __name__ == "__main__":
    test_admin_update()

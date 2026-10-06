import unittest
import json
import os
import database
from app import app
from werkzeug.security import check_password_hash

class ArteDeFavelaTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        if os.path.exists("agenda.db"):
            try:
                os.remove("agenda.db")
            except Exception:
                pass
        database.criar_banco()

    def test_01_seed_dados_iniciais(self):
        """Verifica se os servicos padrao e o usuario admin com hash foram criados"""
        conexao = database.conectar_banco()
        admin = conexao.execute("SELECT * FROM usuarios WHERE nome = 'admin'").fetchone()
        self.assertIsNotNone(admin)
        self.assertTrue(check_password_hash(admin['senha'], 'admin123'))

        servicos = conexao.execute("SELECT COUNT(*) as total FROM servicos").fetchone()
        self.assertGreaterEqual(servicos['total'], 4)

        configs = database.obter_todas_configuracoes()
        self.assertEqual(configs.get('nome_barbearia'), 'Arte de Favela')
        conexao.close()
        print("[OK] Teste 1: Seeds e integridade inicial verificados com sucesso.")

    def test_02_autenticacao_admin(self):
        """Testa login com sucesso e falha, alem da protecao de rotas"""
        resp_fail = self.client.post('/login', json={'nome': 'admin', 'senha': 'errada123'})
        self.assertEqual(resp_fail.status_code, 401)

        resp_ok = self.client.post('/login', json={'nome': 'admin', 'senha': 'admin123'})
        self.assertEqual(resp_ok.status_code, 200)

        client_deslogado = app.test_client()
        resp_redir = client_deslogado.get('/admin/dashboard')
        self.assertEqual(resp_redir.status_code, 302)

        print("[OK] Teste 2: Autenticacao, hash de senha e protecao de rotas funcionando.")

    def test_03_fluxo_agendamento_e_evita_duplicidade(self):
        """Testa agendamento pelo cliente e prevencao de duplicidade"""
        servicos = database.listar_servicos(apenas_ativos=True)
        servico = servicos[0]

        data_teste = "2026-10-16" # Sexta-feira (aberto)
        horario_teste = "14:00"

        payload = {
            "cliente": "Joao da Silva Teste",
            "telefone": "(11) 98888-7777",
            "servico_id": servico["id"],
            "data": data_teste,
            "horario": horario_teste,
            "observacoes": "Degrade navalhado"
        }

        resp = self.client.post('/agendar', json=payload)
        self.assertEqual(resp.status_code, 201)
        data_json = resp.get_json()
        agendamento_id = data_json["agendamento_id"]
        self.assertIsNotNone(agendamento_id)

        # Segundo agendamento no mesmo horario
        payload_duplicado = {
            "cliente": "Outro Cliente",
            "telefone": "(11) 91111-2222",
            "servico_id": servico["id"],
            "data": data_teste,
            "horario": horario_teste
        }
        resp_dup = self.client.post('/agendar', json=payload_duplicado)
        self.assertEqual(resp_dup.status_code, 409)

        # Verificar na grade
        resp_grid = self.client.get(f'/api/horarios-disponiveis?data={data_teste}')
        grid_data = resp_grid.get_json()
        self.assertTrue(grid_data["aberto"])
        slot_14 = next((s for s in grid_data["horarios"] if s["horario"] == horario_teste), None)
        self.assertIsNotNone(slot_14)
        self.assertFalse(slot_14["disponivel"])
        self.assertEqual(slot_14["tipo"], "ocupado")

        print("[OK] Teste 3: Agendamento, grade dinamica e prevencao de conflito validados.")

    def test_04_faturamento_atualizado_com_agendamento(self):
        """Garante que o faturamento atualiza imediatamente ao confirmar agendamento"""
        servicos = database.listar_servicos(apenas_ativos=True)
        s1 = servicos[0] # R$ 35

        data_teste = "2026-10-23" # Sexta-feira
        _, _, id1 = database.criar_novo_agendamento("Cliente 1", "(11) 99999-1111", s1["id"], data_teste, "09:00", status="Agendado")
        _, _, id2 = database.criar_novo_agendamento("Cliente 2", "(11) 99999-2222", s1["id"], data_teste, "10:00", status="Confirmado")

        conexao = database.conectar_banco()
        # Ambos devem somar ao faturamento do dia (status != 'Cancelado')
        fat_dia = conexao.execute("SELECT COALESCE(SUM(valor), 0) as total FROM agendamentos WHERE data = ? AND status != 'Cancelado'", (data_teste,)).fetchone()["total"]
        self.assertEqual(fat_dia, s1["preco"] * 2)

        # Cancelar id1 -> deve subtrair do faturamento
        database.atualizar_status_agendamento(id1, "Cancelado")
        fat_dia_depois = conexao.execute("SELECT COALESCE(SUM(valor), 0) as total FROM agendamentos WHERE data = ? AND status != 'Cancelado'", (data_teste,)).fetchone()["total"]
        self.assertEqual(fat_dia_depois, s1["preco"])
        conexao.close()

        print("[OK] Teste 4: Faturamento atualizado imediatamente com o agendamento comprovado.")

    def test_05_bloqueio_de_horario(self):
        """Testa bloqueio de horario pelo barbeiro em dia util"""
        data_teste = "2026-10-24" # Sabado (aberto)
        horario_bloqueio = "15:00"

        database.adicionar_bloqueio(data_teste, horario_bloqueio, "Consulta medica")

        resp_grid = self.client.get(f'/api/horarios-disponiveis?data={data_teste}')
        grid_data = resp_grid.get_json()
        self.assertTrue(grid_data["aberto"], f"Esperava que {data_teste} estivesse aberto.")
        slot = next((s for s in grid_data["horarios"] if s["horario"] == horario_bloqueio), None)
        self.assertIsNotNone(slot, "Slot deveria estar presente na grade de sabado.")
        self.assertFalse(slot["disponivel"])
        self.assertEqual(slot["tipo"], "bloqueado")

        servicos = database.listar_servicos(apenas_ativos=True)
        sucesso, msg, _ = database.criar_novo_agendamento("Cliente X", "(11) 91234-5678", servicos[0]["id"], data_teste, horario_bloqueio)
        self.assertFalse(sucesso)
        self.assertIn("bloqueado", msg)

        print("[OK] Teste 5: Bloqueio de horarios do barbeiro funcionando perfeitamente.")

    def test_06_dias_fechados_rejeitados(self):
        """Garante que dias que nao sao Sexta nem Sabado sejam bloqueados"""
        quarta_feira = "2026-10-14"
        resp_grid = self.client.get(f'/api/horarios-disponiveis?data={quarta_feira}')
        grid_data = resp_grid.get_json()
        self.assertFalse(grid_data["aberto"])
        self.assertEqual(len(grid_data["horarios"]), 0)

        # Tentativa de agendamento na quarta deve falhar
        servicos = database.listar_servicos(apenas_ativos=True)
        resp_post = self.client.post('/agendar', json={
            "cliente": "Cliente Dia Fechado",
            "telefone": "(11) 99999-8888",
            "servico_id": servicos[0]["id"],
            "data": quarta_feira,
            "horario": "10:00"
        })
        self.assertEqual(resp_post.status_code, 400)
        self.assertIn("Sextas-feiras e aos Sábados", resp_post.get_json()["erro"])

        print("[OK] Teste 6: Bloqueio estrito de dias fechados validado com sucesso.")

if __name__ == "__main__":
    unittest.main()

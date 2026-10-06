import unittest
import database
from app import app

class TestAlmocoEFaturamento(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = app.test_client()
        self.data_teste = "2026-10-16" # Sexta-feira
        # Limpar agendamentos anteriores de teste
        con = database.conectar_banco()
        con.execute("DELETE FROM agendamentos WHERE cliente LIKE ?", ('%Teste Automatizado%',))
        con.commit()
        con.close()

    def tearDown(self):
        con = database.conectar_banco()
        con.execute("DELETE FROM agendamentos WHERE cliente LIKE ?", ('%Teste Automatizado%',))
        con.commit()
        con.close()

    def test_horario_almoco_bloqueado_na_grade(self):
        """Valida que os horários das 13:00 até 14:00 aparecem como almoço e desabilitados."""
        resp = self.client.get(f"/api/horarios-disponiveis?data={self.data_teste}")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["aberto"])
        
        slots_almoco = [s for s in data["horarios"] if s["tipo"] == "almoco"]
        self.assertEqual(len(slots_almoco), 2, "Devem existir 2 slots no almoço: 13:00 e 13:30")
        for slot in slots_almoco:
            self.assertIn(slot["horario"], ["13:00", "14:00"])
            self.assertFalse(slot["disponivel"], f"Horário {slot['horario']} deve estar indisponível para marcação")
            self.assertIn("Almoço", slot["status"])

    def test_rejeicao_agendamento_no_almoco(self):
        """Valida que tentar agendar às 13:00 ou 13:30 resulta em erro e não grava no banco."""
        resp = self.client.post("/agendar", json={
            "cliente": "Teste Automatizado Almoco",
            "telefone": "(11) 99999-1111",
            "servico_id": 1,
            "data": self.data_teste,
            "horario": "13:00"
        })
        self.assertEqual(resp.status_code, 409)
        self.assertIn("almoço", resp.get_json().get("erro", "").lower())

        resp2 = self.client.post("/agendar", json={
            "cliente": "Teste Automatizado Almoco",
            "telefone": "(11) 99999-1111",
            "servico_id": 1,
            "data": self.data_teste,
            "horario": "14:00"
        })
        self.assertEqual(resp2.status_code, 409)
        self.assertIn("almoço", resp2.get_json().get("erro", "").lower())

    def test_faturamento_atualizado_por_horario_marcado(self):
        """Valida que o faturamento é atualizado imediatamente a cada horário marcado pelo cliente."""
        # Obter faturamento antes
        dados_antes = database.obter_dados_faturamento(self.data_teste)
        fat_dia_antes = dados_antes["fat_dia_selecionado"]
        fat_total_antes = dados_antes["fat_total_geral"]

        # Agendar às 14:00 (Combo VIP - R$ 55,00)
        resp = self.client.post("/agendar", json={
            "cliente": "Teste Automatizado Faturamento",
            "telefone": "(11) 98888-2222",
            "servico_id": 4, # R$ 55.00
            "data": self.data_teste,
            "horario": "15:00"
        })
        self.assertEqual(resp.status_code, 201)

        # Obter faturamento depois
        dados_depois = database.obter_dados_faturamento(self.data_teste)
        self.assertEqual(dados_depois["fat_dia_selecionado"], fat_dia_antes + 55.0)
        self.assertEqual(dados_depois["fat_total_geral"], fat_total_antes + 55.0)

        # Validar no gráfico por horário
        slot_14 = next((s for s in dados_depois["grafico_horarios_dia"] if s["horario"] == "14:00"), None)
        self.assertIsNotNone(slot_14)
        self.assertEqual(slot_14["valor"], 55.0)
        self.assertEqual(slot_14["qtd"], 1)
        self.assertIn("Teste Automatizado Faturamento", slot_14["detalhes"])

if __name__ == "__main__":
    unittest.main()

import database
import datetime

def test_faturamento_imediato():
    print("Iniciando teste de faturamento atualizado imediatamente com o agendamento...")

    # 1. Obter faturamento antes do agendamento
    stats_antes = database.obter_estatisticas_dashboard()
    fat_mes_antes = stats_antes["faturamento_mes"]
    fat_total_antes = stats_antes["faturamento_total_confirmado"]
    print(f"Faturamento antes: Mes = R$ {fat_mes_antes:.2f} | Total = R$ {fat_total_antes:.2f}")

    # 2. Criar novo agendamento de Combo (R$ 55,00) para proxima Sexta
    data_teste = "2026-10-16"
    horario_teste = "16:00"
    servico_id = 4 # Combo Arte de Favela (R$ 55,00)
    servico = database.obter_servico_por_id(servico_id)
    valor_servico = servico["preco"]

    sucesso, msg, agendamento_id = database.criar_novo_agendamento(
        cliente_nome="Faturamento Imediato Teste",
        telefone="(11) 96666-5555",
        servico_id=servico_id,
        data=data_teste,
        horario=horario_teste,
        status="Confirmado"
    )
    assert sucesso, f"Erro ao criar agendamento: {msg}"
    print(f"[OK] Agendamento criado com ID {agendamento_id} no valor de R$ {valor_servico:.2f}")

    # 3. Obter faturamento imediatamente depois (sem precisar marcar como concluido!)
    stats_depois = database.obter_estatisticas_dashboard()
    fat_mes_depois = stats_depois["faturamento_mes"]
    fat_total_depois = stats_depois["faturamento_total_confirmado"]
    print(f"Faturamento depois: Mes = R$ {fat_mes_depois:.2f} | Total = R$ {fat_total_depois:.2f}")

    # 4. Validar aumento exato do valor do servico
    assert fat_mes_depois == fat_mes_antes + valor_servico, "O faturamento do mes deve aumentar imediatamente!"
    assert fat_total_depois == fat_total_antes + valor_servico, "O faturamento total confirmado deve aumentar imediatamente!"
    print(f"[OK] Faturamento do mes e total aumentaram com precisao de R$ {valor_servico:.2f}!")

    # 5. Se o agendamento for cancelado, o faturamento deve ser subtraido imediatamente
    database.atualizar_status_agendamento(agendamento_id, "Cancelado")
    stats_cancelado = database.obter_estatisticas_dashboard()
    assert stats_cancelado["faturamento_mes"] == fat_mes_antes, "Ao cancelar, o faturamento deve subtrair o valor!"
    print("[OK] Ao cancelar agendamento, faturamento deduzido corretamente!")

    print("\nTESTE DE FATURAMENTO IMEDIATO CONCLUIDO COM 100% DE SUCESSO!")

if __name__ == "__main__":
    test_faturamento_imediato()

def validar_requisitos(documento):
    erros = []

    if "Como um" not in documento:
        erros.append("Falta a seção de persona (ex: 'Como um ...').")

    if "Critérios de Aceite" not in documento and "ACs" not in documento:
        erros.append("Faltam Critérios de Aceite.")

    return erros
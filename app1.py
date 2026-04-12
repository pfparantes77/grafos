import json
import smtplib
from email.message import EmailMessage
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).parent
CONCEITOS_DIR = BASE_DIR / "data" / "conceitos"
EXERCICIOS_DIR = BASE_DIR / "data" / "exercicios"


def carregar_jsons(pasta: Path):
    itens = []
    for ficheiro in sorted(pasta.glob("*.json")):
        with open(ficheiro, "r", encoding="utf-8") as f:
            itens.append(json.load(f))
    return itens


def calcular_pontos(tentativas_ate_acertar: int) -> int:
    if tentativas_ate_acertar == 1:
        return 3
    if tentativas_ate_acertar == 2:
        return 2
    if tentativas_ate_acertar == 3:
        return 1
    return 0


def atribuir_medalha(pontos: int, pontos_maximos: int):
    if pontos_maximos == 0:
        return "Sem medalha", "Ainda não existem exercícios."
    percentagem = (pontos / pontos_maximos) * 100
    if percentagem >= 90:
        return "🥇 Medalha de Ouro", f"{percentagem:.1f}% da pontuação máxima"
    if percentagem >= 70:
        return "🥈 Medalha de Prata", f"{percentagem:.1f}% da pontuação máxima"
    if percentagem >= 50:
        return "🥉 Medalha de Bronze", f"{percentagem:.1f}% da pontuação máxima"
    return "Sem medalha", f"{percentagem:.1f}% da pontuação máxima. Tens de estudar mais..."


def inicializar_estado(exercicios):
    if "respostas" not in st.session_state:
        st.session_state["respostas"] = {}
    if "tentativas" not in st.session_state:
        st.session_state["tentativas"] = {ex["id"]: 0 for ex in exercicios}
    if "resolvidos" not in st.session_state:
        st.session_state["resolvidos"] = []
    if "pontos" not in st.session_state:
        st.session_state["pontos"] = 0
    if "feedback" not in st.session_state:
        st.session_state["feedback"] = {}
    if "nome_aluno" not in st.session_state:
        st.session_state["nome_aluno"] = ""
    if "turma_aluno" not in st.session_state:
        st.session_state["turma_aluno"] = ""
    if "numero_aluno" not in st.session_state:
        st.session_state["numero_aluno"] = ""


def reiniciar_app(exercicios):
    st.session_state["respostas"] = {}
    st.session_state["tentativas"] = {ex["id"]: 0 for ex in exercicios}
    st.session_state["resolvidos"] = []
    st.session_state["pontos"] = 0
    st.session_state["feedback"] = {}
    st.session_state["nome_aluno"] = ""
    st.session_state["turma_aluno"] = ""
    st.session_state["numero_aluno"] = ""


def enviar_relatorio_email(
    nome_aluno: str,
    turma: str,
    numero: str,
    pontos: int,
    resolvidos: int,
    total_exercicios: int,
    pontos_maximos: int,
    medalha: str,
    detalhe: str,
):
    remetente = st.secrets["email"]["remetente"]
    password = st.secrets["email"]["password"]
    smtp_server = st.secrets["email"]["smtp_server"]
    smtp_port = int(st.secrets["email"]["smtp_port"])

    destinatario = "pedro.arantes@aeamares.com"

    assunto = f"Relatório OP13 - {nome_aluno}"

    corpo = f"""
Relatório automático da aplicação didática - Módulo OP13: Modelos de Grafos

Identificação do aluno
----------------------
Nome: {nome_aluno}
Turma: {turma}
Número: {numero}

Resultados
----------
Exercícios resolvidos: {resolvidos}/{total_exercicios}
Pontuação obtida: {pontos}/{pontos_maximos}
Medalha: {medalha}
Detalhe: {detalhe}
"""

    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destinatario
    msg.set_content(corpo)

    with smtplib.SMTP(smtp_server, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(remetente, password)
        smtp.send_message(msg)


def mostrar_conceitos(conceitos):
    st.title("Modelos de Grafos")
    st.subheader("Glossário")

    if not conceitos:
        st.warning("Não foram encontrados conceitos em ficheiros JSON.")
        return

    for conceito in conceitos:
        with st.expander(conceito.get("titulo", "Conceito"), expanded=False):
            st.markdown(f"**Definição:** {conceito.get('definicao', '')}")
            st.markdown(f"**Exemplo:** {conceito.get('exemplo_texto', '')}")

            imagem = conceito.get("imagem")
            if imagem:
                caminho_imagem = BASE_DIR / imagem
                if caminho_imagem.exists():
                    st.image(str(caminho_imagem), width=200)

            video = conceito.get("video")
            if video:
                caminho_video = BASE_DIR / video
                if caminho_video.exists():
                    st.video(str(caminho_video))
                else:
                    st.info("Vídeo referenciado, mas ainda não encontrado na pasta media/videos.")


def mostrar_exercicios(exercicios):
    st.title("Exercícios de escolha múltipla")

    if not exercicios:
        st.warning("Não foram encontrados exercícios em ficheiros JSON.")
        return

    inicializar_estado(exercicios)

    total = len(exercicios)
    resolvidos = len(st.session_state["resolvidos"])
    st.progress(resolvidos / total if total else 0)
    st.caption(f"Exercícios resolvidos: {resolvidos}/{total}")

    temas = sorted(set(ex.get("tema", "Sem tema") for ex in exercicios))
    tema_escolhido = st.selectbox("Filtrar por tema", ["Todos"] + temas)

    if tema_escolhido != "Todos":
        exercicios_visiveis = [ex for ex in exercicios if ex.get("tema") == tema_escolhido]
    else:
        exercicios_visiveis = exercicios

    for ex in exercicios_visiveis:
        ex_id = ex["id"]
        with st.container(border=True):
            st.markdown(f"### {ex.get('tema', 'Exercício')} — {ex_id}")
            st.write(ex.get("pergunta", ""))

            imagem = ex.get("imagem")
            if imagem:
                caminho_imagem = BASE_DIR / imagem
                if caminho_imagem.exists():
                    st.image(str(caminho_imagem), width=200)

            if ex_id in st.session_state["resolvidos"]:
                st.success("Este exercício já foi resolvido.")
                fb = st.session_state["feedback"].get(ex_id, "")
                if fb:
                    st.info(fb)
                continue

            tentativas_atuais = st.session_state["tentativas"].get(ex_id, 0)
            restantes = max(0, 3 - tentativas_atuais)
            st.caption(f"Tentativas restantes: {restantes}")

            opcoes = ex.get("opcoes", {})
            escolha = st.radio(
                "Seleciona uma opção:",
                options=list(opcoes.keys()),
                format_func=lambda k: f"{k}) {opcoes[k]}",
                key=f"radio_{ex_id}",
            )

            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button("Confirmar resposta", key=f"btn_{ex_id}"):
                    st.session_state["tentativas"][ex_id] += 1
                    tentativa = st.session_state["tentativas"][ex_id]

                    if escolha == ex.get("correta"):
                        pontos = calcular_pontos(tentativa)
                        st.session_state["pontos"] += pontos
                        st.session_state["resolvidos"].append(ex_id)
                        st.session_state["feedback"][ex_id] = (
                            f"Correto à {tentativa}.ª tentativa. "
                            f"Ganhaste {pontos} ponto(s). "
                            f"Explicação: {ex.get('explicacao', '')}"
                        )
                        st.rerun()
                    else:
                        if tentativa >= 3:
                            st.session_state["resolvidos"].append(ex_id)
                            correta = ex.get("correta")
                            st.session_state["feedback"][ex_id] = (
                                f"Sem sucesso após 3 tentativas. "
                                f"Resposta correta: {correta}) {opcoes.get(correta, '')}. "
                                f"Explicação: {ex.get('explicacao', '')}"
                            )
                            st.rerun()
                        else:
                            st.error("Resposta incorreta. Tenta novamente.")

            with col2:
                if st.button("Mostrar explicação", key=f"exp_{ex_id}"):
                    st.info(ex.get("explicacao", "Sem explicação disponível."))


def mostrar_resultados(exercicios):
    inicializar_estado(exercicios)

    st.title("Resultados finais")

    total_exercicios = len(exercicios)
    pontos_maximos = total_exercicios * 3
    pontos = st.session_state.get("pontos", 0)
    resolvidos = len(st.session_state.get("resolvidos", []))

    medalha, detalhe = atribuir_medalha(pontos, pontos_maximos)

    c1, c2, c3 = st.columns(3)
    c1.metric("Pontos totais", pontos)
    c2.metric("Exercícios resolvidos", resolvidos)
    c3.metric("Pontuação máxima", pontos_maximos)

    st.subheader(medalha)
    st.write(detalhe)

    if total_exercicios > 0:
        percentagem_resolucao = (resolvidos / total_exercicios) * 100
        st.write(f"Resolução: {percentagem_resolucao:.1f}% dos exercícios.")

    st.markdown("---")
    st.subheader("Identificação do aluno")

    nome = st.text_input("Nome do aluno", key="nome_aluno")
    turma = st.text_input("Turma", key="turma_aluno")
    numero = st.text_input("Número", key="numero_aluno")

    st.caption(
        "Ao submeter, será enviado um relatório com a identificação e o desempenho do aluno para o email do professor."
    )

    if st.button("Submeter relatório ao professor"):
        nome = nome.strip()
        turma = turma.strip()
        numero = numero.strip()

        if not nome:
            st.error("Indica o nome do aluno antes de submeter.")
        else:
            try:
                enviar_relatorio_email(
                    nome_aluno=nome,
                    turma=turma,
                    numero=numero,
                    pontos=pontos,
                    resolvidos=resolvidos,
                    total_exercicios=total_exercicios,
                    pontos_maximos=pontos_maximos,
                    medalha=medalha,
                    detalhe=detalhe,
                )
                st.success("Relatório enviado com sucesso para o professor.")
            except Exception as e:
                st.error(f"Não foi possível enviar o email: {e}")

    if st.button("Reiniciar progresso"):
        reiniciar_app(exercicios)
        st.rerun()


def main():
    st.set_page_config(
        page_title="Grafos com Streamlit",
        page_icon="🧠",
        layout="wide"
    )

    conceitos = carregar_jsons(CONCEITOS_DIR)
    exercicios = carregar_jsons(EXERCICIOS_DIR)

    inicializar_estado(exercicios)

    st.sidebar.title("Navegação")
    pagina = st.sidebar.radio(
        "Escolhe uma área",
        ["Definições e exemplos", "Exercícios", "Resultados"]
    )

    st.sidebar.markdown("---")
    st.sidebar.write("Aplicação didática para o módulo OP13 — Modelos de Grafos.")

    if pagina == "Definições e exemplos":
        mostrar_conceitos(conceitos)
    elif pagina == "Exercícios":
        mostrar_exercicios(exercicios)
    else:
        mostrar_resultados(exercicios)


if __name__ == "__main__":
    main()

import json
import smtplib
from email.message import EmailMessage
from pathlib import Path
from datetime import datetime
import mimetypes

import streamlit as st

BASE_DIR = Path(__file__).parent
CONCEITOS_DIR = BASE_DIR / "data" / "conceitos"
EXERCICIOS_DIR = BASE_DIR / "data" / "exercicios"
EXERCICIOS_SUBMISSAO_DIR = BASE_DIR / "data" / "exercicios_submissao"


def carregar_jsons(pasta: Path):
    itens = []
    if not pasta.exists():
        return itens

    for ficheiro in sorted(pasta.glob("*.json")):
        try:
            with open(ficheiro, "r", encoding="utf-8") as f:
                dados = json.load(f)

            if isinstance(dados, dict):
                itens.append(dados)
            else:
                st.warning(f"O ficheiro {ficheiro.name} não contém um objeto JSON válido.")
        except Exception as e:
            st.warning(f"Erro ao carregar {ficheiro.name}: {e}")

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

    return "Sem medalha", f"{percentagem:.1f}% da pontuação máxima. Tens de estudar mais."


def inicializar_estado(exercicios_escolha_multipla):
    if "respostas" not in st.session_state:
        st.session_state["respostas"] = {}

    if "tentativas" not in st.session_state:
        st.session_state["tentativas"] = {
            ex["id"]: 0 for ex in exercicios_escolha_multipla if "id" in ex
        }

    if "resolvidos" not in st.session_state:
        st.session_state["resolvidos"] = []

    if "acertados" not in st.session_state:
        st.session_state["acertados"] = []

    if "falhados" not in st.session_state:
        st.session_state["falhados"] = []

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


def reiniciar_app(exercicios_escolha_multipla):
    st.session_state["respostas"] = {}
    st.session_state["tentativas"] = {
        ex["id"]: 0 for ex in exercicios_escolha_multipla if "id" in ex
    }
    st.session_state["resolvidos"] = []
    st.session_state["acertados"] = []
    st.session_state["falhados"] = []
    st.session_state["pontos"] = 0
    st.session_state["feedback"] = {}
    st.session_state["nome_aluno"] = ""
    st.session_state["turma_aluno"] = ""
    st.session_state["numero_aluno"] = ""


def calcular_estatisticas_por_tema(exercicios, acertados_ids, falhados_ids):
    estatisticas = {}

    for ex in exercicios:
        tema = ex.get("tema", "Sem tema")
        ex_id = ex.get("id")

        if tema not in estatisticas:
            estatisticas[tema] = {
                "total": 0,
                "acertados": 0,
                "falhados": 0,
                "resolvidos": 0,
                "percentagem_sucesso": 0.0,
            }

        estatisticas[tema]["total"] += 1

        if ex_id in acertados_ids:
            estatisticas[tema]["acertados"] += 1

        if ex_id in falhados_ids:
            estatisticas[tema]["falhados"] += 1

    for tema, dados in estatisticas.items():
        dados["resolvidos"] = dados["acertados"] + dados["falhados"]
        if dados["total"] > 0:
            dados["percentagem_sucesso"] = (dados["acertados"] / dados["total"]) * 100
        else:
            dados["percentagem_sucesso"] = 0.0

    return estatisticas


def obter_config_email():
    """
    Lê a configuração de email a partir de st.secrets.
    Estrutura esperada no secrets.toml:

    [email]
    remetente = "..."
    password = "..."
    smtp_server = "..."
    smtp_port = "587"
    """
    try:
        email_cfg = st.secrets["email"]
        remetente = email_cfg["remetente"]
        password = email_cfg["password"]
        smtp_server = email_cfg["smtp_server"]
        smtp_port = int(email_cfg["smtp_port"])
        return remetente, password, smtp_server, smtp_port
    except Exception as e:
        raise RuntimeError(
            "Configuração de email inválida em st.secrets. "
            "Verifica se existe a secção [email] com as chaves "
            "'remetente', 'password', 'smtp_server' e 'smtp_port'. "
            f"Erro técnico: {e}"
        )


def enviar_email(msg: EmailMessage):
    remetente, password, smtp_server, smtp_port = obter_config_email()

    try:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(remetente, password)
            smtp.send_message(msg)
    except Exception as e:
        raise RuntimeError(f"Falha no envio SMTP: {e}")


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
    exercicios,
    acertados_ids,
    falhados_ids,
):
    remetente, _, _, _ = obter_config_email()
    destinatario = "pedro.arantes@aeamares.com"

    assunto = f"Relatório OP13 - {nome_aluno}"
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    estatisticas = calcular_estatisticas_por_tema(exercicios, acertados_ids, falhados_ids)

    texto_temas = ""
    for tema, dados in estatisticas.items():
        texto_temas += (
            f"- {tema}\n"
            f"  Total: {dados['total']}\n"
            f"  Resolvidos: {dados['resolvidos']}/{dados['total']}\n"
            f"  Com sucesso: {dados['acertados']}\n"
            f"  Sem sucesso: {dados['falhados']}\n"
            f"  Percentagem de sucesso: {dados['percentagem_sucesso']:.1f}%\n\n"
        )

    corpo = f"""
Relatório automático da aplicação didática - Módulo OP13: Modelos de Grafos

Data e hora da submissão
------------------------
{data_hora}

Identificação do aluno
----------------------
Nome: {nome_aluno}
Turma: {turma}
Número: {numero}

Resultados gerais
-----------------
Exercícios resolvidos: {resolvidos}/{total_exercicios}
Pontuação obtida: {pontos}/{pontos_maximos}
Medalha: {medalha}
Detalhe: {detalhe}

Resultados por tema
-------------------
{texto_temas}
"""

    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destinatario
    msg.set_content(corpo)

    enviar_email(msg)


def enviar_submissao_ficheiro_email(
    nome_aluno: str,
    turma: str,
    numero: str,
    titulo_exercicio: str,
    uploaded_file,
):
    remetente, _, _, _ = obter_config_email()
    destinatario = "pedro.arantes@aeamares.com"

    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    assunto = f"Submissão OP13 - {nome_aluno}"

    corpo = f"""
Foi submetida uma resolução de exercício.

Data e hora
-----------
{data_hora}

Identificação do aluno
----------------------
Nome: {nome_aluno}
Turma: {turma}
Número: {numero}

Exercício
---------
{titulo_exercicio if titulo_exercicio.strip() else "Não indicado"}

Ficheiro enviado
----------------
{uploaded_file.name}
"""

    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destinatario
    msg.set_content(corpo)

    ficheiro_bytes = uploaded_file.getvalue()
    ficheiro_nome = uploaded_file.name

    mime_type = uploaded_file.type
    if not mime_type:
        mime_type, _ = mimetypes.guess_type(ficheiro_nome)

    if mime_type and "/" in mime_type:
        maintype, subtype = mime_type.split("/", 1)
    else:
        maintype, subtype = "application", "octet-stream"

    msg.add_attachment(
        ficheiro_bytes,
        maintype=maintype,
        subtype=subtype,
        filename=ficheiro_nome,
    )

    enviar_email(msg)


def mostrar_glossario(conceitos):
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
                    st.image(str(caminho_imagem), width=250)

            video = conceito.get("video")
            if video:
                caminho_video = BASE_DIR / video
                if caminho_video.exists():
                    st.video(str(caminho_video))
                else:
                    st.info("Vídeo referenciado, mas não encontrado na pasta indicada.")


def mostrar_videos_tutoriais():
    st.title("Vídeos tutoriais")
    st.write("Nesta área podes consultar vídeos de apoio à resolução de exercícios e à compreensão dos conceitos.")

    videos = [
        {
            "titulo": "Introdução aos grafos",
            "tipo": "url",
            "fonte": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "descricao": "Substitui este link pelo vídeo que pretenderes."
        },
        {
            "titulo": "Circuitos de Euler",
            "tipo": "local",
            "fonte": BASE_DIR / "media" / "videos" / "euler.mp4",
            "descricao": "Exemplo de vídeo armazenado localmente."
        },
        {
            "titulo": "Circuitos de Hamilton",
            "tipo": "local",
            "fonte": BASE_DIR / "media" / "videos" / "hamilton.mp4",
            "descricao": "Exemplo de vídeo armazenado localmente."
        },
    ]

    for video in videos:
        with st.container(border=True):
            st.subheader(video["titulo"])
            st.write(video["descricao"])

            if video["tipo"] == "url":
                st.video(video["fonte"])
            elif video["tipo"] == "local":
                if Path(video["fonte"]).exists():
                    st.video(str(video["fonte"]))
                else:
                    st.warning(f"Vídeo não encontrado: {Path(video['fonte']).name}")


def mostrar_exercicios_escolha_multipla(exercicios):
    st.title("Exercícios de escolha múltipla")

    st.info(
        "Nesta área podes resolver exercícios organizados por tema.\n\n"
        "Começa por escolher um tema, ou mantém a opção 'Todos' para ver todos os exercícios disponíveis. "
        "Podes tentar resolver cada exercício até 3 vezes.\n\n"
        "Se acertares à 1.ª tentativa ganhas 3 pontos, à 2.ª ganhas 2 pontos e à 3.ª ganhas 1 ponto.\n\n"
        "Se não acertares após 3 tentativas, o exercício fica concluído sem pontuação.\n\n"
        "No final, podes consultar os teus resultados globais e o teu desempenho por tema."
    )

    if not exercicios:
        st.warning("Não foram encontrados exercícios de escolha múltipla.")
        return

    inicializar_estado(exercicios)

    total = len(exercicios)
    resolvidos = len(st.session_state["resolvidos"])
    st.progress(resolvidos / total if total else 0)
    st.caption(f"Exercícios resolvidos: {resolvidos}/{total}")

    temas = sorted(set(ex.get("tema", "Sem tema") for ex in exercicios))
    tema_escolhido = st.selectbox("Filtrar por tema", ["Todos"] + temas, key="tema_em")

    if tema_escolhido != "Todos":
        exercicios_visiveis = [ex for ex in exercicios if ex.get("tema") == tema_escolhido]
    else:
        exercicios_visiveis = exercicios

    for ex in exercicios_visiveis:
        ex_id = ex.get("id")
        if not ex_id:
            continue

        with st.container(border=True):
            st.markdown(f"### {ex.get('tema', 'Exercício')} — {ex_id}")
            st.write(ex.get("pergunta", ""))

            imagem = ex.get("imagem")
            if imagem:
                caminho_imagem = BASE_DIR / imagem
                if caminho_imagem.exists():
                    st.image(str(caminho_imagem), width=250)

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
            if not opcoes:
                st.warning("Este exercício não tem opções definidas.")
                continue

            escolha = st.radio(
                "Seleciona uma opção:",
                options=list(opcoes.keys()),
                format_func=lambda k: f"{k}) {opcoes[k]}",
                key=f"radio_{ex_id}",
            )

            if st.button("Confirmar resposta", key=f"btn_{ex_id}"):
                st.session_state["tentativas"][ex_id] += 1
                tentativa = st.session_state["tentativas"][ex_id]

                if escolha == ex.get("correta"):
                    pontos = calcular_pontos(tentativa)
                    st.session_state["pontos"] += pontos
                    st.session_state["resolvidos"].append(ex_id)
                    st.session_state["acertados"].append(ex_id)
                    st.session_state["feedback"][ex_id] = (
                        f"Correto à {tentativa}.ª tentativa. "
                        f"Ganhaste {pontos} ponto(s). "
                        f"Explicação: {ex.get('explicacao', '')}"
                    )
                    st.rerun()
                else:
                    if tentativa >= 3:
                        st.session_state["resolvidos"].append(ex_id)
                        st.session_state["falhados"].append(ex_id)
                        correta = ex.get("correta")
                        st.session_state["feedback"][ex_id] = (
                            f"Sem sucesso após 3 tentativas. "
                            f"Resposta correta: {correta}) {opcoes.get(correta, '')}. "
                            f"Explicação: {ex.get('explicacao', '')}"
                        )
                        st.rerun()
                    else:
                        st.error("Resposta incorreta. Tenta novamente.")


def mostrar_pdf_exercicio(caminho_pdf: Path, chave_unica: str):
    if caminho_pdf.exists():
        with open(caminho_pdf, "rb") as f:
            pdf_bytes = f.read()

        st.download_button(
            label="Abrir / descarregar enunciado em PDF",
            data=pdf_bytes,
            file_name=caminho_pdf.name,
            mime="application/pdf",
            key=chave_unica,
        )
    else:
        st.warning("O ficheiro PDF do enunciado não foi encontrado.")


def mostrar_exercicios_submissao(exercicios_submissao):
    st.title("Exercícios de submissão")
    st.write("Resolve o exercício no teu caderno, numa folha ou em formato digital, e carrega a tua resolução.")

    if not exercicios_submissao:
        st.warning("Não foram encontrados exercícios de submissão.")
        return

    temas = sorted(set(ex.get("tema", "Sem tema") for ex in exercicios_submissao))
    tema_escolhido = st.selectbox("Filtrar por tema", ["Todos"] + temas, key="tema_submissao")

    if tema_escolhido != "Todos":
        exercicios_visiveis = [ex for ex in exercicios_submissao if ex.get("tema") == tema_escolhido]
    else:
        exercicios_visiveis = exercicios_submissao

    opcoes_exercicios = {}

    for ex in exercicios_visiveis:
        ex_id = ex.get("id", "")
        titulo = ex.get("titulo", "")
        tema = ex.get("tema", "Exercício")

        identificador = f"{ex_id} - {titulo}" if titulo else ex_id
        if identificador.strip():
            opcoes_exercicios[identificador] = ex_id

        with st.container(border=True):
            st.markdown(f"### {tema} — {ex_id}")
            if titulo:
                st.write(f"**{titulo}**")

            descricao_curta = ex.get("descricao_curta", "")
            if descricao_curta:
                st.write(descricao_curta)

            enunciado = ex.get("enunciado", "")
            if enunciado:
                st.write(enunciado)

            imagem = ex.get("imagem")
            if imagem:
                caminho_imagem = BASE_DIR / imagem
                if caminho_imagem.exists():
                    st.image(str(caminho_imagem), width=250)

            pdf_relativo = ex.get("pdf")
            if pdf_relativo:
                caminho_pdf = BASE_DIR / pdf_relativo
                mostrar_pdf_exercicio(caminho_pdf, chave_unica=f"pdf_{ex_id}")

            criterios = ex.get("criterios", [])
            if criterios:
                st.markdown("**Critérios de sucesso:**")
                for criterio in criterios:
                    st.write(f"- {criterio}")

    st.markdown("---")
    st.info(
        "Carrega apenas a resolução do exercício. "
        "Evita fotografias com rostos ou outros dados pessoais desnecessários."
    )

    with st.form("form_submissao_resolucao", clear_on_submit=True):
        nome = st.text_input("Nome do aluno")
        turma = st.text_input("Turma")
        numero = st.text_input("Número")

        exercicio_escolhido = st.selectbox(
            "Seleciona o exercício a submeter",
            options=[""] + list(opcoes_exercicios.keys())
        )

        uploaded_file = st.file_uploader(
            "Carrega a tua resolução",
            type=["png", "jpg", "jpeg", "pdf"]
        )

        submeter = st.form_submit_button("Submeter resolução ao professor")

        if submeter:
            if not nome.strip():
                st.error("Indica o nome do aluno.")
                return

            if not exercicio_escolhido.strip():
                st.error("Seleciona o exercício a submeter.")
                return

            if uploaded_file is None:
                st.error("Carrega um ficheiro antes de submeter.")
                return

            tamanho_maximo_mb = 15
            tamanho_bytes = len(uploaded_file.getvalue())
            if tamanho_bytes > tamanho_maximo_mb * 1024 * 1024:
                st.error(f"O ficheiro excede o limite de {tamanho_maximo_mb} MB.")
                return

            try:
                enviar_submissao_ficheiro_email(
                    nome_aluno=nome.strip(),
                    turma=turma.strip(),
                    numero=numero.strip(),
                    titulo_exercicio=exercicio_escolhido.strip(),
                    uploaded_file=uploaded_file,
                )
                st.success("Submissão enviada com sucesso para o professor.")
            except Exception as e:
                st.error(f"Não foi possível enviar a submissão: {e}")


def mostrar_resultados(exercicios_escolha_multipla):
    inicializar_estado(exercicios_escolha_multipla)

    st.title("Resultados")

    total_exercicios = len(exercicios_escolha_multipla)
    pontos_maximos = total_exercicios * 3
    pontos = st.session_state.get("pontos", 0)
    resolvidos_ids = st.session_state.get("resolvidos", [])
    acertados_ids = st.session_state.get("acertados", [])
    falhados_ids = st.session_state.get("falhados", [])

    resolvidos = len(resolvidos_ids)
    acertados = len(acertados_ids)
    falhados = len(falhados_ids)

    medalha, detalhe = atribuir_medalha(pontos, pontos_maximos)
    estatisticas = calcular_estatisticas_por_tema(exercicios_escolha_multipla, acertados_ids, falhados_ids)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pontos totais", pontos)
    c2.metric("Exercícios resolvidos", resolvidos)
    c3.metric("Com sucesso", acertados)
    c4.metric("Sem sucesso", falhados)

    st.subheader(medalha)
    st.write(detalhe)

    if total_exercicios > 0:
        percentagem_resolucao = (resolvidos / total_exercicios) * 100
        st.write(f"Resolução: {percentagem_resolucao:.1f}% dos exercícios.")

    st.markdown("---")
    st.subheader("Desempenho por tema")

    for tema, dados in estatisticas.items():
        with st.container(border=True):
            st.write(f"**Tema:** {tema}")
            st.write(f"Total de exercícios: {dados['total']}")
            st.write(f"Resolvidos: {dados['resolvidos']}/{dados['total']}")
            st.write(f"Com sucesso: {dados['acertados']}")
            st.write(f"Sem sucesso: {dados['falhados']}")
            st.write(f"Percentagem de sucesso: {dados['percentagem_sucesso']:.1f}%")

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
                    exercicios=exercicios_escolha_multipla,
                    acertados_ids=acertados_ids,
                    falhados_ids=falhados_ids,
                )
                st.success("Relatório enviado com sucesso para o professor.")
            except Exception as e:
                st.error(f"Não foi possível enviar o email: {e}")

    if st.button("Reiniciar progresso"):
        reiniciar_app(exercicios_escolha_multipla)
        st.rerun()


def main():
    st.set_page_config(
        page_title="Grafos com Streamlit",
        page_icon="🧠",
        layout="wide"
    )

    conceitos = carregar_jsons(CONCEITOS_DIR)
    exercicios_escolha_multipla = carregar_jsons(EXERCICIOS_DIR)
    exercicios_submissao = carregar_jsons(EXERCICIOS_SUBMISSAO_DIR)

    inicializar_estado(exercicios_escolha_multipla)

    st.sidebar.title("Percurso de aprendizagem")
    pagina = st.sidebar.radio(
        "Escolhe uma área",
        [
            "Glossário",
            "Vídeos tutoriais",
            "Exercícios de escolha múltipla",
            "Exercícios de submissão",
            "Resultados"
        ]
    )

    st.sidebar.markdown("---")
    st.sidebar.write("Aplicação didática para o módulo OP13 — Modelos de Grafos.")

    if pagina == "Glossário":
        mostrar_glossario(conceitos)
    elif pagina == "Vídeos tutoriais":
        mostrar_videos_tutoriais()
    elif pagina == "Exercícios de escolha múltipla":
        mostrar_exercicios_escolha_multipla(exercicios_escolha_multipla)
    elif pagina == "Exercícios de submissão":
        mostrar_exercicios_submissao(exercicios_submissao)
    else:
        mostrar_resultados(exercicios_escolha_multipla)


if __name__ == "__main__":
    main()

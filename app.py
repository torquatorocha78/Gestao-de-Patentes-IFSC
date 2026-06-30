import streamlit as st
import pandas as pd
from datetime import date
import database as db

# =====================================================
# CONFIGURAÇÃO DA PÁGINA
# =====================================================

st.set_page_config(
    page_title="Gestão de Patentes - IFSC",
    page_icon="📄",
    layout="wide",
)

db.init_database()

# =====================================================
# FUNÇÕES AUXILIARES (APP)
# =====================================================

def emoji_status(status):
    if status == "PENDENTE":
        return "🟢"
    if status == "PAGA":
        return "✅"
    return "⚪"


# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.title("📌 Menu")

pagina = st.sidebar.radio(
    "Selecione",
    [
        "Dashboard",
        "Cadastrar Patente",
        "Minhas Patentes",
        "Importar Excel",
    ],
)

# =====================================================
# DASHBOARD
# =====================================================

if pagina == "Dashboard":
    st.title("📊 Dashboard Geral")

    df_patentes = db.obter_patentes()

    total_patentes = len(df_patentes)
    total_pendentes = 0
    total_pagas = 0

    for _, patente in df_patentes.iterrows():
        anuidades = db.obter_anuidades(patente["id"])

        total_pendentes += len(anuidades[anuidades["status"] == "PENDENTE"])
        total_pagas += len(anuidades[anuidades["status"] == "PAGA"])

    col1, col2, col3 = st.columns(3)

    col1.metric("Total de Patentes", total_patentes)
    col2.metric("Anuidades Pendentes", total_pendentes)
    col3.metric("Anuidades Pagas", total_pagas)

# =====================================================
# CADASTRAR PATENTE
# =====================================================

elif pagina == "Cadastrar Patente":
    st.title("➕ Cadastrar Nova Patente")

    with st.form("form_patente"):
        numero = st.text_input("Número da Patente")
        data_dep = st.date_input("Data de Depósito")
        data_conc = st.date_input("Data de Concessão", value=None)
        descricao = st.text_area("Descrição")
        titular = st.text_input("Titular")

        submitted = st.form_submit_button("Salvar")

        if submitted:
            sucesso, msg = db.adicionar_patente(
                numero,
                data_dep,
                data_conc,
                descricao,
                titular,
            )

            if sucesso:
                st.success(msg)
            else:
                st.error(msg)

# =====================================================
# MINHAS PATENTES
# =====================================================

elif pagina == "Minhas Patentes":
    st.title("📁 Minhas Patentes")

    df_patentes = db.obter_patentes()

    if df_patentes.empty:
        st.info("Nenhuma patente cadastrada.")
    else:
        for _, patente in df_patentes.iterrows():
            with st.expander(f"📄 {patente['numero_patente']}"):
                st.write(f"**Titular:** {patente['titular']}")
                st.write(f"**Data de Depósito:** {patente['data_deposito'].date()}")
                st.write(f"**Descrição:** {patente['descricao']}")

                anuidades = db.obter_anuidades(patente["id"])

                # 🔹 Resumo: mostrar apenas pendentes
                pendentes = anuidades[anuidades["status"] == "PENDENTE"]

                st.subheader("Resumo")
                if pendentes.empty:
                    st.success("Todas as anuidades estão pagas ✅")
                else:
                    proxima = pendentes.iloc[0]
                    st.warning(
                        f"Próxima anuidade pendente: "
                        f"{proxima['numero_anuidade']}ª"
                    )

                st.subheader("Anuidades")

                tabela = []
                for _, a in anuidades.iterrows():
                    tabela.append(
                        {
                            "Anuidade": a["numero_anuidade"],
                            "Início Ordinário": a["data_inicio_ordinario"].date(),
                            "Fim Ordinário": a["data_fim_ordinario"].date(),
                            "Fim Extraordinário": a["data_fim_extraordinario"].date(),
                            "Status": f"{emoji_status(a['status'])} {a['status']}",
                        }
                    )

                st.dataframe(pd.DataFrame(tabela), use_container_width=True)

                # 🔹 Registrar pagamento manual
                st.subheader("Registrar Pagamento")

                pendentes_nums = pendentes["numero_anuidade"].tolist()

                if pendentes_nums:
                    with st.form(f"pagamento_{patente['id']}"):
                        num_anuidade = st.selectbox(
                            "Anuidade",
                            pendentes_nums,
                        )
                        data_pag = st.date_input(
                            "Data do Pagamento",
                            value=date.today(),
                        )

                        pagar = st.form_submit_button("Registrar")

                        if pagar:
                            db.atualizar_status_anuidade(
                                patente["id"],
                                num_anuidade,
                                "pago",
                                data_pag,
                            )
                            st.success("Pagamento registrado com sucesso!")
                            st.rerun()
                else:
                    st.info("Nenhuma anuidade pendente.")

# =====================================================
# IMPORTAR EXCEL
# =====================================================

elif pagina == "Importar Excel":
    st.title("📥 Importar Patentes via Excel")

    arquivo = st.file_uploader(
        "Selecione o arquivo Excel",
        type=["xlsx"],
    )

    if arquivo:
        resultados = db.importar_excel(arquivo)

        st.subheader("Resultado da Importação")

        df_res = pd.DataFrame(
            resultados,
            columns=["Número da Patente", "Sucesso", "Mensagem"],
        )

        st.dataframe(df_res, use_container_width=True)

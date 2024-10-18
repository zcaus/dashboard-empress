import locale
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime, timedelta

# Configuração da página com título e favicon
st.set_page_config(
    page_title="Sistema de Controle",
    page_icon="planilha/mascote_instagram-removebg-preview.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Configuração inicial do locale e da página
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'C')  # Fallback para 'C' se 'pt_BR.UTF-8' falhar

# Estilos customizados do Streamlit
st.markdown(
    """
    <style>
        .main {
            background-color: rgba(0, 0, 0, 0.2);
        }
        .sidebar .sidebar-content {
            background-color: rgba(0, 0, 0, 0.2);
        }
        .blinking-yellow {
            animation: blinker 1s linear infinite;
            color: yellow;
            background-color: rgba(255, 255, 0, 0.1);
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 5px;
        }
        .blinking-red {
            animation: blinker 1s linear infinite;
            color: red;
            background-color: rgba(255, 0, 0, 0.1);
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 5px;
        }
        .stApp {
        background: url("") no-repeat center center fixed;
        background-size: cover;
        opacity: 80%;
        }
        @keyframes blinker {
            80% { opacity: 0; }
        }
        
    </style>
    """,
    unsafe_allow_html=True
)

# Ocultar colunas desnecessárias
colunas_para_ocultar = ['Emp', 'Código', 'Razão', 'UF', 'Tp.Venda', 'F.Pagto', 'Vendedor', '% Comissão', 'Operador', '% Comissão.1', '% ICMS', '% IPI', 'Vl.Desc.']

# Carregar os dados e ocultar colunas desnecessárias
@st.cache_data
def load_data(file_path='planilha/PEDIDOS_VOLPE8.XLSX'):
    try:
        df = pd.read_excel(file_path)
        return df.drop(columns=colunas_para_ocultar, errors='ignore')
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        return pd.DataFrame()

df = load_data()

df['Valor Unit.'] = pd.to_numeric(df['Valor Unit.'], errors='coerce')
df['Qtd.'] = pd.to_numeric(df['Qtd.'], errors='coerce')

# Substituir NaN por 0
df['Valor Unit.'].fillna(0, inplace=True)
df['Qtd.'].fillna(0, inplace=True)

# Multiplicação segura
df['Valor Total'] = df['Valor Unit.'] * df['Qtd.']

# Excluindo linhas com uma condição específica
df = df[df['UN'] != 'KG']

# Exemplo: Remover linhas com 'Fantasia' em uma lista específica
df = df[~df['Fantasia'].isin(['PRIME', 'AMD 5', 'AMD 10', 'FREXCO', 'SESC INTERLAGOS', 'RODRIGO MELO', 'FOXMIX', 'CCINTER ANTÔNIO', 'L A REFRIGERACAO', 'NACAO NATURAL'])]

df['Status'] = 'Pendente'

# Calcular o total de pedidos únicos
total_pedidos = df['Ped. Cliente'].nunique()

# Exibir o total de pedidos como uma linha adicional
estatisticas_gerais = pd.DataFrame({
    'Estatística': ['Total de Pedidos'],
    'Valor': [total_pedidos]
})

# Atualizar status dos pedidos da "COLINA"
def atualizar_status_colina(df):
    status_dict = {}
    pedidos_colina = df[df['Fantasia'] == 'COLINA']['Nr.pedido'].astype(str)
    for pedido in pedidos_colina:
        if '-' in pedido:
            base = pedido.split('-')[0]
            status_dict[base] = 'Entregue'
            status_dict[pedido] = 'Pendente'
        else:
            if pedido not in status_dict:
                status_dict[pedido] = 'Entregue'
    for pedido in pedidos_colina:
        if '-' in pedido:
            base = pedido.split('-')[0]
            sufixo_num = int(pedido.split('-')[1])
            for i in range(sufixo_num):
                status_dict[f"{base}-{i:02}"] = 'Entregue'
    df['Status'] = df.apply(lambda row: status_dict.get(str(row['Nr.pedido']), row['Status']) if row['Fantasia'] == 'COLINA' else row['Status'], axis=1)
    df['Status_Atualizado'] = df['Fantasia'] == 'COLINA'

atualizar_status_colina(df)

# Atualiza status de outros pedidos
now = datetime.now()
df['Dt.fat.'] = pd.to_datetime(df['Dt.fat.'], errors='coerce')
df['Prev.entrega'] = pd.to_datetime(df['Prev.entrega'], errors='coerce')

def update_status(row):
    if row['Status_Atualizado']:
        return row['Status']
    if pd.isnull(row['Dt.fat.']):
        return 'Atrasado' if row['Prev.entrega'] < now else 'Pendente'
    return 'Entregue'

df['Status'] = df.apply(update_status, axis=1)
df.drop(columns='Status_Atualizado', inplace=True)

# Contagem de pedidos pendentes e atrasados
pendente = (df['Status'] == 'Pendente').sum()
atrasado = (df['Status'] == 'Atrasado').sum()

# Seleção de perfil
perfil = st.sidebar.selectbox("Selecione o Perfil", ["ADM", "Separação", "Compras"])

# Converte colunas de data
df['Dt.pedido'] = pd.to_datetime(df['Dt.pedido'], format='%d/%m/%Y', dayfirst=True)
df['Valor Total'] = df['Valor Unit.'] * df['Qtd.']
df['Valor Total'] = df['Valor Total'].apply(lambda x: locale.currency(x, grouping=True, symbol=None))

# Função para criar o gráfico de pizza com a porcentagem de status
def create_percentage_chart(df):
    total_pedidos = df['Status'].value_counts()
    total = total_pedidos.sum()
    percentage = (total_pedidos / total) * 100
    percentage_summary = percentage.reset_index()
    percentage_summary.columns = ['Status', 'Percentual']
    pie_chart = px.pie(percentage_summary, values='Percentual', names='Status', title='Porcentagem de Pedidos por Status')
    return pie_chart

# Função para criar o gráfico de barras com valor total por status
def create_value_bar_chart(df):
    df['Valor Total Numérico'] = df['Valor Total'].apply(lambda x: locale.atof(x.strip()))
    df_filtrado = df[df['Status'].isin(['Pendente', 'Atrasado', 'Entregue'])]
    total_por_status = df_filtrado.groupby('Status')['Valor Total Numérico'].sum().reset_index()
    total_por_status.columns = ['Status', 'Valor Total']
    bar_chart = px.bar(total_por_status, x='Status', y='Valor Total', text='Valor Total', title='Valor Total por Status', labels={'Valor Total': 'Valor Total (R$)', 'Status': '  '})
    return bar_chart

# Exibição dos gráficos no Streamlit
st.title("Dashboard de Controle de Pedidos")
st.plotly_chart(create_percentage_chart(df))
st.plotly_chart(create_value_bar_chart(df))

import locale
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime,timedelta

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
    locale.setlocale(locale.LC_ALL, 'C')  # ou 'en_US.UTF-8' como fallback

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
        opacity: 80%
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
def load_data(file_path='planilha/PEDIDOS_VOLPE7.XLSX'):
    try:
        df = pd.read_excel(file_path)
        return df.drop(columns=colunas_para_ocultar, errors='ignore')
    except Exception as e:
        st.error(f"Erro ao carregar os dados: {e}")
        return pd.DataFrame()

df = load_data()

df['Valor Unit.'] = pd.to_numeric(df['Valor Unit.'], errors='coerce')
df['Qtd.'] = pd.to_numeric(df['Qtd.'], errors='coerce')

# Substituir NaN por 0, ou trate de outra forma, conforme a necessidade
df['Valor Unit.'].fillna(0, inplace=True)
df['Qtd.'].fillna(0, inplace=True)

# Agora é seguro multiplicar
df['Valor Total'] = df['Valor Unit.'] * df['Qtd.']

print(df[['Valor Unit.', 'Qtd.', 'Valor Total']])

# Excluindo linhas com uma condição específica
# Exemplo: Remover linhas onde a coluna 'UN' é igual a 'KG'
df = df[df['UN'] != 'KG']

# Exemplo: Remover linhas com 'Fantasia' em uma lista específica
df = df[~df['Fantasia'].isin(['PRIME', 'AMD 5', 'AMD 10', 'FREXCO','SESC INTERLAGOS','RODRIGO MELO','FOXMIX','CCINTER ANTÔNIO', 'L A REFRIGERACAO','NACAO NATURAL'])]

df['Status'] = 'Pendente'

def atualizar_status_colina(df):
    status_dict = {}

    # Filtra apenas os pedidos com fantasia "COLINA"
    pedidos_colina = df[df['Fantasia'] == 'COLINA']['Nr.pedido'].astype(str)

    # Itera para definir status
    for pedido in pedidos_colina:
        if '-' in pedido:
            base = pedido.split('-')[0]
            status_dict[base] = 'Entregue'
            status_dict[pedido] = 'Pendente'
        else:
            if pedido not in status_dict:
                status_dict[pedido] = 'Entregue'

    # Ajusta os status com base nos sufixos maiores
    for pedido in pedidos_colina:
        if '-' in pedido:
            base = pedido.split('-')[0]
            sufixo_num = int(pedido.split('-')[1])
            for i in range(sufixo_num):
                status_dict[f"{base}-{i:02}"] = 'Entregue'

    # Atualiza a coluna 'Status' apenas para pedidos da 'COLINA'
    df['Status'] = df.apply(
        lambda row: status_dict.get(str(row['Nr.pedido']), row['Status']) if row['Fantasia'] == 'COLINA' else row['Status'], 
        axis=1
    )

    # Cria uma coluna auxiliar para indicar quais linhas foram atualizadas
    df['Status_Atualizado'] = df['Fantasia'] == 'COLINA'

# Aplica a função para atualizar o status para pedidos "COLINA"
atualizar_status_colina(df)

# Define a função `update_status` somente para pedidos não atualizados
now = datetime.now()
df['Dt.fat.'] = pd.to_datetime(df['Dt.fat.'], errors='coerce')
df['Prev.entrega'] = pd.to_datetime(df['Prev.entrega'], errors='coerce')

def update_status(row):
    if row['Status_Atualizado']:
        return row['Status']  # Retorna o status já definido pela função anterior
    if pd.isnull(row['Dt.fat.']):
        return 'Atrasado' if row['Prev.entrega'] < now else 'Pendente'
    return 'Entregue'

# Atualiza status, respeitando as linhas que já foram atualizadas
df['Status'] = df.apply(update_status, axis=1)

# Remove a coluna auxiliar
df.drop(columns='Status_Atualizado', inplace=True)

# Contagem de pedidos pendentes e atrasados
pendente = (df['Status'] == 'Pendente').sum()
atrasado = (df['Status'] == 'Atrasado').sum()

# Seleção de perfil
perfil = st.sidebar.selectbox("Selecione o Perfil", ["ADM", "Separação", "Compras"])

# Converte colunas de data e calcula 'Valor Total'
df['Dt.pedido'] = pd.to_datetime(df['Dt.pedido'], format='%d/%m/%Y', dayfirst=True)
df['Valor Total'] = df['Valor Unit.'] * df['Qtd.']
df['Valor Total'] = df['Valor Total'].apply(lambda x: f'R${x:,.2f}')

def calcular_pendentes_atrasados(df):
    pendentes = (df['Status'] == 'Pendente').sum()
    atrasados = (df['Status'] == 'Atrasado').sum()
    return pendentes, atrasados

# Criação de gráficos
def create_percentage_chart(df):
    # Contando o total de pedidos por status
    total_pedidos = df['Status'].value_counts()
    
    # Calculando a porcentagem
    total = total_pedidos.sum()
    percentage = (total_pedidos / total) * 100
    
    percentage_summary = percentage.reset_index()
    percentage_summary.columns = ['Status', 'Percentual']
    
    # Gráfico de pizza para mostrar a porcentagem
    pie_chart = px.pie(percentage_summary, 
                       values='Percentual', 
                       names='Status', 
                       title='Porcentagem de Pedidos por Status')

    return pie_chart

# Função para criar o gráfico de barras com o valor total em R$ apenas para status Pendente e Atrasado
def create_value_bar_chart(df):
   # Remove o prefixo 'R$' e converte para float na coluna 'Valor Total'
    df['Valor Total Numérico'] = df['Valor Total'].str.replace('R$', '').str.replace(',', '.').astype(float)

    # Filtra o DataFrame para incluir os status "Pendente", "Atrasado" e "Entregue"
    df_filtrado = df[df['Status'].isin(['Pendente', 'Atrasado', 'Entregue'])]

    # Agrupa os dados por status e calcula o valor total em R$
    total_por_status = df_filtrado.groupby('Status')['Valor Total Numérico'].sum().reset_index()
    total_por_status.columns = ['Status', 'Valor Total']

    # Cria o gráfico de barras
    bar_chart = px.bar(
        total_por_status, 
        x='Status', 
        y='Valor Total', 
        text='Valor Total', 
        title='Valor Total por Status',
        labels={'Valor Total': 'Valor Total (R$)', 'Status': 'Status'}
    )
    
    return bar_chart
# Funções de cada guia
def guia_dashboard():
    st.markdown("<h3>Estatísticas Gerais <small style='font-size: 0.4em;'></small></h3>", unsafe_allow_html=True)
    st.metric("Total de Produtos", len(df))
    st.metric("Total de Produtos Pendentes", pendente)
    st.metric("Total de Produtos Atrasados", atrasado)
    
    col1, col2 = st.columns(2)

    with col1:
    # Exibe o gráfico de porcentagem de pedidos por status
        st.plotly_chart(create_percentage_chart(df))

    with col2:
    # Exibe o gráfico de barras por status
        st.plotly_chart(create_value_bar_chart(df))

def guia_carteira():
    st.title("Carteira")
    
    # Filtrando o DataFrame para ocultar linhas com UN igual a KG
    df_filtrado = df[df['UN'] != 'KG']
    
    cliente_selecionado = st.selectbox("Selecione o Cliente", ["Todos os Clientes"] + df_filtrado['Fantasia'].unique().tolist())
    pedidos_cliente = df_filtrado if cliente_selecionado == "Todos os Clientes" else df_filtrado[df_filtrado['Fantasia'] == cliente_selecionado]
    
    pedido_filtro = st.text_input("Filtrar por número de pedido:")
    status_filtro = st.selectbox("Filtrar por Status", ["Todos", "Pendente", "Atrasado", "Entregue"])
    
    if pedido_filtro:
        pedidos_cliente = pedidos_cliente[pedidos_cliente['Ped. Cliente'].astype(str).str.contains(pedido_filtro)]
    
    if status_filtro != "Todos":
        pedidos_cliente = pedidos_cliente[pedidos_cliente['Status'] == status_filtro]

    # Exibir número de linhas após a filtragem
    total_linhas_depois = pedidos_cliente.shape[0]
    st.write(f"Número de linhas: {total_linhas_depois}")
    
    st.dataframe(pedidos_cliente, use_container_width=True)
    total_valor = (pedidos_cliente['Valor Unit.'] * pedidos_cliente['Qtd.']).sum()
    st.metric("Total (R$)", locale.currency(total_valor, grouping=True, symbol=None))

def guia_notificacoes():
    st.title("Notificações")
    st.write("Todas novidades do Sistema e Atualizações serão notificadas neste campo.")

def mover_pedidos(df):
    # Filtra os pedidos que têm '-' no Nr.pedido
    pedidos_com_hifen = df[df['Nr.pedido'].astype(str).str.contains('-')]
    pedidos_sem_hifen = df[~df['Nr.pedido'].astype(str).str.contains('-')]
    
    # Atualiza o DataFrame de separação e compras
    compras_df = pedidos_com_hifen[pedidos_com_hifen['Status'].isin(['Pendente'])]
    separacao_df = pedidos_sem_hifen[pedidos_sem_hifen['Status'] == 'Pendente']
    
    return separacao_df, compras_df

# Modificações na guia de Separação/Expedição
def guia_separacao():
    st.title("Separação")
    
    separacao_df, _ = mover_pedidos(df)
    separacao_df = separacao_df[(separacao_df['Status'] == 'Pendente') | (~separacao_df['Status'].str.contains('-'))]
    separacao_df = separacao_df.dropna(axis=1, how='all')
    # Adicionando a lógica para verificar se o pedido está atrasado
    today = datetime.now()

    # Verificar se a coluna 'Dt. pedido' existe antes de proceder
    if 'Dt.pedido' in separacao_df.columns:
        # Convertendo a coluna 'Dt. pedido' para datetime
        separacao_df['Dt.pedido'] = pd.to_datetime(separacao_df['Dt.pedido'], errors='coerce')
        
        # Verificando se a data do pedido é mais antiga que 2 dias a partir de hoje
        separacao_df['Atrasado'] = (today - separacao_df['Dt.pedido']) > timedelta(days=2)
        
        # Atualizando o status para 'Atrasado' se o pedido estiver atrasado e ainda 'Pendente'
        separacao_df.loc[(separacao_df['Atrasado']) & (separacao_df['Status'] == 'Pendente'), 'Status'] = 'Atrasado'
    else:
        st.warning("A coluna 'Dt.pedido' não foi encontrada no DataFrame.")

    pendentes_sep, atrasados_sep = calcular_pendentes_atrasados(separacao_df)
    if pendentes_sep > 0:
        st.sidebar.markdown(f'<div class="blinking-yellow">Atenção: Você possui {pendentes_sep} produto(s) pendente(s) no total!</div>', unsafe_allow_html=True)
    if atrasados_sep > 0:
        st.sidebar.markdown(f'<div class="blinking-red">Atenção: Você possui {atrasados_sep} produto(s) atrasado(s) no total!</div>', unsafe_allow_html=True)

    # Filtros
    cliente_selecionado = st.selectbox("Selecione o Cliente", ["Todos os Clientes"] + separacao_df['Fantasia'].unique().tolist())
    separacao_df = separacao_df if cliente_selecionado == "Todos os Clientes" else separacao_df[separacao_df['Fantasia'] == cliente_selecionado]

    pedido_filtro = st.text_input("Filtrar por número de pedido:")
    status_filtro = st.selectbox("Filtrar por Status", ["Todos", "Pendente", "Atrasado"])
    
    if pedido_filtro:
        separacao_df = separacao_df[separacao_df['Ped. Cliente'].astype(str).str.contains(pedido_filtro)]
    
    if status_filtro != "Todos":
        separacao_df = separacao_df[separacao_df['Status'] == status_filtro]

    # Exibir número de linhas após a filtragem
    total_linhas_depois = separacao_df.shape[0]
    st.write(f"Número de linhas: {total_linhas_depois}")

    # Exibe o DataFrame filtrado e o total específico
    st.dataframe(separacao_df, use_container_width=True)
    total_valor = (separacao_df['Valor Unit.'] * separacao_df['Qtd.']).sum()
    st.metric("Total (R$)", locale.currency(total_valor, grouping=True, symbol=None))

# Modificações na guia de Compras
def guia_compras():
    st.title("Compras")
    
    # DataFrame geral para calcular pendentes e atrasados (antes dos filtros)
    _, compras_df_geral = mover_pedidos(df)
    compras_df_geral = compras_df_geral[(compras_df_geral['Status'] == 'Pendente') | (compras_df_geral['Status'].str.contains('-'))]
    
    # Calcular o total geral de pendentes e atrasados
    pendentes_compras_geral, atrasados_compras_geral = calcular_pendentes_atrasados(compras_df_geral)
    
    # Notificações baseadas no total geral
    if pendentes_compras_geral > 0:
        st.sidebar.markdown(f'<div class="blinking-yellow">Atenção: Você possui {pendentes_compras_geral} produto(s) pendente(s) no total!</div>', unsafe_allow_html=True)
    if atrasados_compras_geral > 0:
        st.sidebar.markdown(f'<div class="blinking-red">Atenção: Você possui {atrasados_compras_geral} produto(s) atrasado(s) no total!</div>', unsafe_allow_html=True)
    
    # Filtragem para exibição
    _, compras_df = mover_pedidos(df)
    compras_df = compras_df[(compras_df['Status'] == 'Pendente') | (compras_df['Status'].str.contains('-'))]
    compras_df = compras_df.dropna(axis=1, how='all')

    # Aplicação dos filtros ao DataFrame
    cliente_selecionado = st.selectbox("Selecione o Cliente", ["Todos os Clientes"] + compras_df['Fantasia'].unique().tolist())
    compras_df = compras_df if cliente_selecionado == "Todos os Clientes" else compras_df[compras_df['Fantasia'] == cliente_selecionado]

    pedido_filtro = st.text_input("Filtrar por número de pedido:")
    status_filtro = st.selectbox("Filtrar por Status", ["Todos", "Pendente", "Atrasado"])
    
    if pedido_filtro:
        compras_df = compras_df[compras_df['Ped. Cliente'].astype(str).str.contains(pedido_filtro)]
    
    if status_filtro != "Todos":
        compras_df = compras_df[compras_df['Status'] == status_filtro]

    total_linhas_depois = compras_df.shape[0]
    st.write(f"Número de linhas: {total_linhas_depois}")

    # Exibe o DataFrame filtrado e o total específico
    st.dataframe(compras_df, use_container_width=True)
    total_valor = (compras_df['Valor Unit.'] * compras_df['Qtd.']).sum()
    st.metric("Total (R$)", locale.currency(total_valor, grouping=True, symbol=None))

    
# Interface por perfil - mantém a estrutura atual
if perfil == "ADM":
    aba = st.sidebar.radio("Escolha uma aba", ["Dashboard", "Carteira", "Notificações"])
    if aba == "Dashboard":
        guia_dashboard()
    elif aba == "Carteira":
        guia_carteira()
    elif aba == "Notificações":
        guia_notificacoes()
    # Notificações de pendência e atraso
    if pendente > 0:
        st.sidebar.markdown(f'<div class="blinking-yellow">Atenção: Você possui {pendente} produto(s) pendente(s)!</div>', unsafe_allow_html=True)
    if atrasado > 0:
        st.sidebar.markdown(f'<div class="blinking-red">Atenção: Você possui {atrasado} produto(s) atrasado(s)!</div>', unsafe_allow_html=True)

else:
    guia_notificacoes()
    if perfil == "Separação":
        guia_separacao()
    elif perfil == "Compras":
        guia_compras()
    
# Salvar alterações (somente ADM)
@st.cache_data(ttl=3600, persist=True)
def save_changes():
    df.to_excel('planilha/pedidos_volpe3_atualizado.xlsx', index=False)

if perfil == "ADM" and st.button("Salvar Alterações"):
    save_changes()
    st.success("Alterações salvas com sucesso!")
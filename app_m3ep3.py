# Importando as bibliotecas necessárias
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import streamlit as st

class M3EP():
    
    def __init__(self):
        pass
   
    def read_data(self, filepath, pattern='funceme'):
        if pattern == 'bdmep':
            data = pd.read_csv(filepath, skiprows=10, sep=';', decimal='.') 
            data['Data Medicao'] = pd.to_datetime(data['Data Medicao'], format='%Y-%m-%d')
            data.drop('Unnamed: 2', axis=1, inplace=True)
            data.columns = ['date', 'daily_pr_mm']
            data.date = pd.to_datetime(data.date)
            data.set_index('date', inplace=True)
        elif pattern == 'funceme':
            data = pd.read_csv(filepath, sep=';', decimal='.') 
            data['data'] = pd.to_datetime(data['data'], format='%Y-%m-%d')
            data.drop('id', axis=1, inplace=True)
            data.drop('posto', axis=1, inplace=True)
            data.columns = ['daily_pr_mm', 'date']
            data.date = pd.to_datetime(data.date)
            data.set_index('date', inplace=True)
            data.sort_index(inplace=True)
        self.data_ = data

    def remove_zero_pr(self):
        column = self.data_.columns[0]
        return self.data_[self.data_[column] > 0]
   
    def select_by_date(self, start_date, end_date):
        data = self.data_.loc[start_date:end_date]
        self.data_ = data
   
    def count_events(self, lower_limit, upper_limit):
        events = self.data_.query(f'daily_pr_mm >= {lower_limit} & daily_pr_mm < {upper_limit}')
        n_events = len(events)
        return n_events
    
    def m3ep(self, quantile=.95, filepath=None, pattern='funceme',
             start_date=None, end_date=None):
        
        if filepath:
            self.read_data(filepath, pattern=pattern)
            
        if start_date:
            self.select_by_date(start_date, end_date)
        
        data = self.remove_zero_pr()
        column = data.columns[0]
        limiar = data.quantile(quantile).values[0]
        data_m3ep = data[data[column] >= limiar]
        median = data_m3ep.median().values[0]
        std = data_m3ep.std().values[0]
        very_strong = median + 2*std
        strong = median + 1*std
        moderated = median
        n_events_moderated = int(self.count_events(moderated, strong))
        n_events_strong = int(self.count_events(strong, very_strong))
        n_events_very_strong = int(self.count_events(very_strong, data.max()[0]+10))
        
        self.result_ = {
            'moderado': {'limiar': round(moderated, 1), 'n eventos': n_events_moderated},
            'forte': {'limiar': round(strong, 1), 'n eventos': n_events_strong},
            'muito forte': {'limiar': round(very_strong, 1), 'n eventos': n_events_very_strong}
        }

        # Adicionando gráficos para cada evento extremo
        self.event_plots_ = {}
        for threshold in ['moderado', 'forte', 'muito forte']:
            limiar = self.result_[threshold]['limiar']
            eventos = data[data[column] >= limiar]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=eventos.index, y=eventos['daily_pr_mm'], mode='lines', name='Precipitação diária'))
            fig.update_layout(title=f'Eventos Extremos - Limiar {threshold.capitalize()} ({limiar} mm)',
                              xaxis_title='Data',
                              yaxis_title='Precipitação (mm)',
                              showlegend=True)
            self.event_plots_[threshold] = fig


# Criando a aplicação Streamlit
st.title("Metodologia Estatística dos Eventos Extremos de Precipitação")
st.header('M3EP')

m3ep = M3EP()

st.subheader('1º Carregar os dados')
uploaded_files = st.file_uploader("Carregue aqui seu(s) arquivo(s) com dados de precipitação:",
                                 accept_multiple_files=True)

st.subheader('1.2 Definir padrão de formatação do arquivo')
st.write('Este programa foi desenvolvido para trabalhar com arquivos CSV no padrão do FUNCEME.')
st.write('Atualmente os padrões de formatação aceitos são: CSV FUNCEME')

st.subheader('2º Definição do quantil limiar')
quantile = st.slider('Selecione o quantil extremo que deseja utilizar.', 90, 100, 95) / 100

st.subheader('3º Definir período de interesse')
st.write('Defina aqui o período (data inicial e data final) para o qual deseja calcular os extremos de precipitação.')
start_date = st.date_input('Data Inicial',
                           datetime(1900, 1, 1))

end_date = st.date_input('Data final',
                         datetime.today())

st.subheader('4º Resultados')
resultados = {}
for uploaded_file in uploaded_files:
    m3ep.m3ep(filepath=uploaded_file,
              quantile=quantile,
              start_date=start_date,
              end_date=end_date
              )
    st.write('Resultados do arquivo:', uploaded_file.name)
    st.write(m3ep.result_)
    resultados[uploaded_file.name[:-4]] = m3ep.result_

# Adicionando gráficos para cada limiar de eventos extremos
if hasattr(m3ep, 'event_plots_'):
    st.subheader('5º Gráficos de Eventos Extremos')
    for threshold, plot in m3ep.event_plots_.items():
        st.plotly_chart(plot, use_container_width=True)

st.subheader('6º Exportar resultados para JSON')
@st.cache
def convert_df(df):
    return df.to_json().encode('utf-8')

json = convert_df(pd.DataFrame(resultados))

st.download_button(
    label="Salve os resultados como JSON",
    data=json,
    file_name=f'm3ep_resultados_{start_date}-{end_date}.json',
    mime='text/json',
)

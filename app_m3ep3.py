import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import streamlit as st

class M3EP():
    
    def __init__(self):
        pass
   
    def read_data(self, filepath, pattern='bdmep'):
        if pattern == 'bdmep':
            data = pd.read_csv(filepath, skiprows=10, sep=';', decimal=',') 
            if 'Data Medicao' not in data.columns:
                st.error("Cabeçalho 'Data Medicao' não encontrado no arquivo.")
                return
            # Tentar adivinhar o formato da data
            data['Data Medicao'] = pd.to_datetime(data['Data Medicao'], errors='coerce') 
            if data['Data Medicao'].isnull().sum() > 0:
                st.error("Falha ao converter a coluna 'Data Medicao' para formato de data. Verifique se o formato é correto.")
                return
            if 'Unnamed: 3' in data.columns:
                data.drop('Unnamed: 3', axis=1, inplace=True)
            data.columns = ['Data Medicao', 'PRECIPITACAO TOTAL DIARIO (AUT)(mm)', 'TEMPERATURA MEDIA DIARIA (AUT)(°C)']
            data.set_index('Data Medicao', inplace=True)
        else:
            print('You need to specify how to read a new pattern.')
            data = None
        self.data_ = data

    def remove_zero_pr(self):
        column = self.data_.columns[0]
        return self.data_[self.data_[column] > 0]
   
    def select_by_date(self, start_date, end_date):
        data = self.data_.loc[start_date:end_date]
        self.data_ = data
   
    def count_events(self, lower_limit, upper_limit):
        events = self.data_.query(f'`PRECIPITACAO TOTAL DIARIO (AUT)(mm)` >= {lower_limit} & `PRECIPITACAO TOTAL DIARIO (AUT)(mm)` < {upper_limit}')
        n_events = len(events)
        return n_events
    
    def m3ep(self, quantile=.95, filepath=None, pattern='inmet',
             start_date=None, end_date=None):
        
        if filepath:
            self.read_data(filepath, pattern=pattern)
            
        if start_date:
            self.select_by_date(start_date, end_date)
        
        if self.data_ is None:
            return
        
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
            'moderado': {'limiar': round(moderated, 2), 'n eventos': n_events_moderated},
            'forte': {'limiar': round(strong, 2), 'n eventos': n_events_strong},
            'muito forte': {'limiar': round(very_strong, 2), 'n eventos': n_events_very_strong}
        }
        
        self.events_data_ = {
            'moderado': data[data[column] >= moderated],
            'forte': data[(data[column] >= strong) & (data[column] < very_strong)],
            'muito forte': data[data[column] >= very_strong]
        }

st.title("Metodologia Estatística dos Eventos Extremos de Precipitação")
st.header('M3EP')

m3ep = M3EP()

st.subheader('1º Carregar os dados')
uploaded_files = st.file_uploader("Carregue aqui seu(s) arquivo(s) com dados de precipitação:",
                                 accept_multiple_files=True)

st.subheader('1.2 Definir padrão de formatação do arquivo')
st.write('Este programa foi desenvolvido, inicialmente, para trabalhar com arquivos CSV no padrão do BDMEP.')
st.write('Atualmente os padrões de formatação aceitos são: BDMEP')
st.write('Caso deseje utilizar outro padrão de arquivo edite o método `read_data` do arquivo `m3ep.py`')

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
              end_date=end_date,
              pattern='bdmep')
    st.write('Resultados do arquivo:', uploaded_file.name)
    formatted_results = {
        'moderado': {'limiar': f"{m3ep.result_['moderado']['limiar']:.2f}", 'n eventos': m3ep.result_['moderado']['n eventos']},
        'forte': {'limiar': f"{m3ep.result_['forte']['limiar']:.2f}", 'n eventos': m3ep.result_['forte']['n eventos']},
        'muito forte': {'limiar': f"{m3ep.result_['muito forte']['limiar']:.2f}", 'n eventos': m3ep.result_['muito forte']['n eventos']}
    }
    st.table(formatted_results)  # Visualizador de tabela estilo Excel
    resultados[uploaded_file.name[:-4]] = formatted_results

st.subheader('5º Exportar resultados para JSON')
def convert_df(df):
    return df.to_json().encode('utf-8')

json = convert_df(pd.DataFrame(resultados))
st.download_button(
    label="Salve os resultados como JSON",
    data=json,
    file_name=f'm3ep_resultados_{start_date}-{end_date}.json',
    mime='text/json',
)

st.subheader('6º Gráficos dos Eventos')
for category in m3ep.events_data_:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=m3ep.events_data_[category].index, y=m3ep.events_data_[category]['PRECIPITACAO TOTAL DIARIO (AUT)(mm)'],
                             mode='lines', name='Precipitação diária', marker=dict(color='blue')))
    fig.update_layout(title=f'Eventos de precipitação igual ou superior ao limiar de {category}',
                      xaxis_title='Data',
                      yaxis_title='Precipitação (mm)',
                      showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

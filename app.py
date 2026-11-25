import streamlit as st
import pandas as pd

st.set_page_config(
  page_title="Análise PC",
  page_icon=":material/insights:",
  layout="wide"
)

@st.fragment(parallel=True)
def card(label: str, value: str | int, icon: str, delta=None, delta_color="normal", chart=None, chart_type=None, help=None, delta_description=None) -> None:
  st.metric(
    f"{label}",
    value,
    icon=icon,
    border=True,
    delta=delta,
    delta_color=delta_color,
    chart_data=chart,
    chart_type=chart_type,
    delta_description=delta_description,
    help=help,
    height="stretch"
  )

def _ceil_to(v, base):
  return ((int(v) + base - 1) // base) * base

entrada_saida = pd.read_csv('entrada_saida.csv')
aporte_pendente_serie = pd.read_csv('aporte_pendente_serie.csv')

entrada_saida['gap'] = entrada_saida['pcs'] - entrada_saida['concluidas']
entrada_saida['backlog'] = entrada_saida['gap'].cumsum()
entrada_saida['aporte_backlog'] = aporte_pendente_serie['Recurso - Aportado']
entrada_saida['aporte_backlog_acumulado'] = entrada_saida['aporte_backlog'].cumsum()

chart_df = (
  entrada_saida
  .reset_index()
  .assign(
    ano=lambda d: d['Ano Base'].astype(str),
    concluidas_acumulado=lambda d: d['concluidas'].cumsum(),
    aporte_mi=lambda d: d['aporte_backlog_acumulado'] / 1e6,
  )
  .rename(columns={'backlog': 'backlog_acumulado'})[
    ['ano', 'concluidas_acumulado', 'backlog_acumulado', 'aporte_mi']
  ]
)

split = 5
pcs_max = _ceil_to(chart_df[['concluidas_acumulado', 'backlog_acumulado']].max().max(), 100)
aporte_max = _ceil_to(chart_df['aporte_mi'].max(), 30)

with st.container(horizontal=True, vertical_alignment="center"):
  with st.container(gap=None):
    st.title("Análise PC - Demanda e Dimensionamento de Equipe", icon=":material/insights:", anchor=False)
    
with st.container(horizontal=False, vertical_alignment="center", border=True):
  st.subheader("Evolução anual do acumulado de concluídas, backlog e aporte", anchor=False)

  st.echarts_chart(
    {
      "legend": {
        "top": 0,
        "left": "center",
        "data": [
          "Concluídas (acumulado)",
          "Backlog (acumulado)",
          "Aporte em backlog (acumulado)",
        ],
      },
      "tooltip": {"trigger": "axis"},
      "grid": {"left": "3%", "right": "4%", "top": 60, "bottom": "3%", "containLabel": True},
      "dataset": {"source": chart_df},
      "xAxis": {"type": "category"},
      "yAxis": [
        {
          "type": "value",
          "name": "PCs",
          "min": 0,
          "max": pcs_max,
          "interval": pcs_max / split,
        },
        {
          "type": "value",
          "name": "Aporte (R$ mi)",
          "min": 0,
          "max": aporte_max,
          "interval": aporte_max / split,
        },
      ],
      "series": [
        {
          "type": "bar",
          "name": "Concluídas (acumulado)",
          "encode": {"x": "ano", "y": "concluidas_acumulado"},
        },
        {
          "type": "bar",
          "name": "Backlog (acumulado)",
          "encode": {"x": "ano", "y": "backlog_acumulado"},
        },
        {
          "type": "line",
          "name": "Aporte em backlog (acumulado)",
          "yAxisIndex": 1,
          "encode": {"x": "ano", "y": "aporte_mi"},
        },
      ],
    },
    alt="Evolução anual do acumulado de PCs concluídas e do backlog (barras) e do aporte em backlog (linha)",
  )
  
st.subheader("Planejamento de cenário (simulação de zerar o backlog)", anchor=False)

st.info(
  "O simulador estima em quanto tempo o **backlog de prestações de contas** seria zerado, "
  "dado o tamanho e a produtividade da equipe. Aqui, consideramos um número de **2 analistas fixos** "
  "correspondentes à equipe atual, com eficiência variável devido a divisão da dedicação entre outras "
  "demandas, mais um número (variável) de **analistas extras** hipoteticamente "
  "dedicados 100% às prestações.\n\n"
  "**Analista-mês** é a unidade de trabalho: 1 analista-mês equivale ao que **um analista "
  "produz em um mês**. Foi considerado uma média de 7 prestações de editais e 15 de eventos/patrocínio por mês.",
  icon=":material/info:",
  title="Como funciona o simulador",
)

atuais_qtd = 2
cap_edital_mes = 7
cap_eps_mes = 15
meses_uteis = 11
anos = entrada_saida['Ano Base'].nunique()

backlog_edital = 554
backlog_eps = 190
backlog_meses = max(backlog_edital / cap_edital_mes, backlog_eps / cap_eps_mes)

n_edital = 839
n_eps = 195
demanda_meses = max(n_edital / cap_edital_mes, n_eps / cap_eps_mes) / anos

with st.container(horizontal=True, gap="small", vertical_alignment="center"):
  cols = st.columns(2, border=True)
  
  with cols[0]:
    atuais_eficiencia = st.slider("Eficiência atual", 0, 100, 70, step=5, format="%d%%") / 100
  with cols[1]:
    extras_100 = st.slider("Analistas extras (100%)", 0, 20, 3, step=1)

fte = extras_100 + atuais_qtd * atuais_eficiencia
capacidade = fte * meses_uteis
saldo = capacidade - demanda_meses

if saldo > 0:
  tempo = backlog_meses / saldo
  tempo_label = f"{tempo:.1f} anos"
else:
  tempo_label = "—"

with st.container(horizontal=True, vertical_alignment="center", gap="small"):
  cols = st.columns(2)
  
  with cols[0]:
    with st.container(horizontal=True):
      card(
        "FTE",
        f"{fte:.1f}",
        icon=":material/groups:",
        help=f"{extras_100} (100%) + {atuais_qtd} × {atuais_eficiencia:.0%}",
      )
      card(
        "Capacidade",
        f"{capacidade:.1f} analista-meses/ano",
        icon=":material/speed:",
        help=f"FTE × {meses_uteis} meses úteis",
      )
      
    with st.container(horizontal=True):
      card(
        "Demanda média",
        f"{demanda_meses:.1f} analista-meses/ano",
        icon=":material/monitoring:",
        help=f"Esforço médio anual das novas PCs: todo o trabalho que chega num ano típico, se fosse feito por 1 analista dedicado, levaria {demanda_meses:.1f} meses.",
      )
      card(
        "Demanda backlog",
        f"{backlog_meses:.1f} analista-meses/ano",
        icon=":material/pending_actions:",
        help="Esforço do backlog",
      )
      
    with st.container(horizontal=True):
      card(
        "Saldo p/ backlog",
        f"{saldo:.1f} analista-meses/ano",
        icon=":material/trending_up:",
        help=f"Capacidade − demanda média",
      )
      card(
        "Tempo p/ zerar",
        tempo_label,
        icon=":material/hourglass_bottom:",
        help="Backlog ÷ saldo",
      )
    
  with cols[1]:
    if saldo <= 0:
      st.warning(
        "Capacidade insuficiente: o saldo é menor ou igual a zero, o backlog não será reduzido.",
        icon=":material/warning:",
      )

    sim = []
    rest = backlog_meses
    ano = 0
    while rest > 0 and saldo > 0 and ano < 100:
      ano += 1
      rest = max(rest - saldo, 0)
      sim.append({"Ano": ano, "Backlog restante (analista-meses)": round(rest, 1)})

    sim_df = pd.DataFrame(sim)

    if not sim_df.empty:
      st.area_chart(
        sim_df,
        x="Ano",
        y="Backlog restante (analista-meses)",
        x_label="Ano",
        y_label="Backlog restante (analista-meses)",
        alt="Simulação da redução do backlog em analista-meses ao longo dos anos",
      )
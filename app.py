import streamlit as st
import pandas as pd
import pdfplumber
import datetime
import io
import re
from fpdf import FPDF
import xlsxwriter

# Configuração da Página
st.set_page_config(page_title="Calculadora Jurídica PC/AL", page_icon="⚖️", layout="wide")

# ------------------------------------------------------------------------------
# 1. FUNÇÕES DE PROCESSAMENTO E EXTRAÇÃO
# ------------------------------------------------------------------------------

def extrair_financeiro(file):
    """Extrai dados financeiro do PDF usando Regex para maior resiliência."""
    with pdfplumber.open(file) as pdf:
        tabela = []
        ano = None
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            
            # Identifica o Ano de Competência
            match_ano = re.search(r"Ano Comp:\s*(\d{4})", text)
            if match_ano: ano = int(match_ano.group(1))

            lines = text.split("\n")
            for line in lines:
                # O código 126.00 identifica o subsídio
                if "126.00 SUBSIDIO" in line:
                    valores_encontrados = re.findall(r"(\d{1,3}(?:\.\d{3})*,\d{2})", line)
                    if len(valores_encontrados) >= 12 and ano:
                        meses = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
                        for i, val in enumerate(valores_encontrados[:12]):
                            val_float = float(val.replace(".", "").replace(",", "."))
                            data = f"{ano}-{meses[i]}"
                            tabela.append({"Data": data, "Valor_Pago": val_float})
        return pd.DataFrame(tabela)

def calcular_base_ano(base_inicial):
    """Gera tabela de evolução da Base A-I."""
    reajustes = {
        2015: 1.05, 2018: 1.0295, 2022: 1.10, 2025: 1.0393
    }
    base_por_ano = {}
    atual = base_inicial
    for ano in range(2014, datetime.datetime.now().year + 1):
        if ano in reajustes: atual *= reajustes[ano]
        base_por_ano[ano] = atual
    return base_por_ano

def calcular_valor_devido(base_A_I, classe_idx, nivel_idx):
    """Calcula o valor 'Dever Ser' (Lei 7.602/14) para exibição na tela."""
    return (base_A_I * (1.15 ** classe_idx)) + (base_A_I * 0.05 * nivel_idx)

# ------------------------------------------------------------------------------
# 2. FUNÇÃO GERADORA DE EXCEL (COM FÓRMULAS AUDITÁVEIS)
# ------------------------------------------------------------------------------
def gerar_excel_formulas(df_final, base_inicial):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    workbook = writer.book

    # --- ABA PARAMETROS ---
    reajustes_map = calcular_base_ano(base_inicial)
    df_params = pd.DataFrame(list(reajustes_map.items()), columns=['Ano', 'Valor_Base'])
    df_params.to_excel(writer, sheet_name='Parametros', index=False)

    # --- ABA CÁLCULO DETALHADO ---
    # Prepara os dados estáticos
    df_export = df_final[['Data', 'Classe', 'Nivel', 'Valor_Pago']].copy()
    df_export['Data'] = pd.to_datetime(df_export['Data']) # Formato data para o Excel entender
    
    df_export.to_excel(writer, sheet_name='Calculo', index=False)
    worksheet = writer.sheets['Calculo']
    
    # Formatações
    fmt_currency = workbook.add_format({'num_format': 'R$ #,##0.00'})
    fmt_date = workbook.add_format({'num_format': 'mm/yyyy'})
    fmt_green = workbook.add_format({'bg_color': '#D4EFDF', 'num_format': 'R$ #,##0.00', 'bold': True})
    fmt_header = workbook.add_format({'bold': True, 'bg_color': '#2C3E50', 'font_color': 'white'})

    # Cabeçalhos Extras
    extras = ['Base Ref', 'Idx Cl', 'Idx Nv', 'VALOR DEVIDO', 'DIFERENÇA', 'Projefweb']
    for i, col_name in enumerate(extras):
        worksheet.write(0, 4 + i, col_name, fmt_header)

    # Escreve Fórmulas linha a linha
    for i in range(len(df_export)):
        row = i + 1 # Excel index (linha 2 em diante)
        xl_row = row + 1 
        
        # Formata Data e Valor Pago
        worksheet.write_datetime(row, 0, df_export.iloc[i, 0], fmt_date)
        worksheet.write_number(row, 3, df_export.iloc[i, 3], fmt_currency)

        # E: Base Ref (PROCV no Ano)
        worksheet.write_formula(row, 4, f'=VLOOKUP(YEAR(A{xl_row}),Parametros!$A:$B,2,TRUE)', fmt_currency)
        
        # F: Index Classe
        worksheet.write_formula(row, 5, f'=MATCH(B{xl_row},{{"A","B","C","D","E","F","G"}},0)-1')
        
        # G: Index Nivel
        worksheet.write_formula(row, 6, f'=MATCH(C{xl_row},{{"I","II","III","IV"}},0)-1')
        
        # H: VALOR DEVIDO (A Mágica da Lei)
        # =(Base * 1.15^Classe) + (Base * 0.05 * Nivel)
        worksheet.write_formula(row, 7, f'=(E{xl_row}*(1.15^F{xl_row}))+(E{xl_row}*0.05*G{xl_row})', fmt_green)
        
        # I: Diferença
        worksheet.write_formula(row, 8, f'=MAX(0, H{xl_row}-D{xl_row})', fmt_currency)
        
        # J: Texto Projefweb
        worksheet.write_formula(row, 9, f'=IF(I{xl_row}>0, TEXT(A{xl_row},"mm-yyyy") & " " & TEXT(I{xl_row}, "R$ #,##0.00"), "")')

    worksheet.set_column('A:A', 12)
    worksheet.set_column('H:I', 18)
    worksheet.set_column('J:J', 25)
    
    writer.close()
    output.seek(0)
    return output

# ------------------------------------------------------------------------------
# 3. INTERFACE STREAMLIT
# ------------------------------------------------------------------------------

st.title("⚖️ Calculadora PC/AL - Lei 7.602/14")
st.markdown("Cálculo de Retroativos com Progressão Geométrica (15%) e Nível (5%)")

with st.sidebar:
    st.header("1. Upload e Config")
    arquivos = st.file_uploader("Fichas Financeiras (PDF)", type=["pdf"], accept_multiple_files=True)
    base_classe_A = st.number_input("Base Classe A (2014)", value=3178.00)
    
    st.header("2. Histórico de Promoções")
    if "historico" not in st.session_state: st.session_state.historico = []
    
    c_data = st.text_input("Data Promoção (AAAA-MM-DD)", "2016-03-01")
    col1, col2 = st.columns(2)
    c_classe = col1.selectbox("Classe", ["A", "B", "C", "D", "E", "F", "G"])
    c_nivel = col2.selectbox("Nível", ["I", "II", "III", "IV"])
    
    if st.button("➕ Adicionar"):
        st.session_state.historico.append((c_data, c_classe, c_nivel))
    
    if st.button("Limpar Histórico"):
        st.session_state.historico = []

    # Mostra histórico
    for item in sorted(st.session_state.historico):
        st.caption(f"{item[0]} | {item[1]} - {item[2]}")

if st.button("🚀 Processar Cálculo") and arquivos and st.session_state.historico:
    try:
        # 1. Extração
        dfs = [extrair_financeiro(f) for f in arquivos]
        df_fin = pd.concat(dfs).sort_values(by="Data").drop_duplicates(subset="Data")

        # 2. Cruzamento de Promoções
        promo_df = pd.DataFrame(st.session_state.historico, columns=["Data", "Classe", "Nivel"])
        promo_df["Data"] = pd.to_datetime(promo_df["Data"]).dt.to_period('M').dt.to_timestamp()
        
        data_inicio = promo_df["Data"].min()
        data_fim = pd.to_datetime(datetime.datetime.now())
        all_months = pd.date_range(data_inicio, data_fim, freq='MS')
        
        df_hist = pd.DataFrame({"Data": all_months})
        df_hist = pd.merge(df_hist, promo_df, on="Data", how="left").ffill()
        df_hist["Data"] = df_hist["Data"].dt.strftime("%Y-%m")

        # 3. Merge Final
        df_final = pd.merge(df_fin, df_hist, on="Data", how="inner")
        
        # 4. Cálculos para Exibição na Tela (Python Puro)
        base_ano_map = calcular_base_ano(base_classe_A)
        df_final["Ano"] = df_final["Data"].str[:4].astype(int)
        df_final["Base_Ref"] = df_final["Ano"].map(base_ano_map)
        df_final["Cl_Idx"] = df_final["Classe"].map(lambda x: ord(x.upper()) - ord("A"))
        df_final["Nv_Idx"] = df_final["Nivel"].map({"I": 0, "II": 1, "III": 2, "IV": 3})
        
        df_final["Valor_Devido"] = df_final.apply(lambda r: calcular_valor_devido(r["Base_Ref"], r["Cl_Idx"], r["Nv_Idx"]), axis=1)
        df_final["Diferenca"] = (df_final["Valor_Devido"] - df_final["Valor_Pago"]).clip(lower=0)
        
        total = df_final["Diferenca"].sum()
        
        st.success(f"Cálculo Concluído! Total Estimado: R$ {total:,.2f}")
        st.dataframe(df_final[["Data", "Classe", "Nivel", "Valor_Pago", "Valor_Devido", "Diferenca"]])

        # 5. Botões de Download
        excel_data = gerar_excel_formulas(df_final, base_classe_A)
        
        st.download_button(
            label="📥 Baixar Planilha Excel (Com Fórmulas)",
            data=excel_data,
            file_name="Calculo_Juridico_Auditavel.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Erro: {e}")

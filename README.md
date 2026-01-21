# ⚖️ Calculadora de Passivos - Polícia Civil de Alagoas (PC/AL)

Ferramenta automatizada para cálculo de diferenças salariais com base na **Lei Estadual nº 7.602/2014**. O sistema reconstrói a tabela salarial correta aplicando a progressão geométrica de 15% entre classes, identificando o "achatamento" salarial praticado pelo Estado.

## 🚀 Funcionalidades

* **Extração Inteligente:** Lê Fichas Financeiras (PDF) do Portal do Servidor via Regex.
* **Cálculo Jurídico Preciso:**
    * Reconstrói a "Base Classe A" considerando os reajustes gerais (2015, 2018, 2022, etc).
    * Aplica interstício de **15% (juros compostos)** entre Classes.
    * Aplica adicional de **5% (sobre a base)** entre Níveis.
* **Exportação Auditável:** Gera planilha Excel (`.xlsx`) com as **fórmulas abertas**, permitindo conferência por peritos judiciais.
* **Padrão Projefweb:** Gera coluna de texto formatada para importação no sistema do Tribunal de Justiça de Alagoas.

## 🛠️ Como Executar Localmente

1.  Clone o repositório:
    ```bash
    git clone [https://github.com/SEU_USUARIO/calculadora-pcal.git](https://github.com/SEU_USUARIO/calculadora-pcal.git)
    ```
2.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```
3.  Execute o aplicativo:
    ```bash
    streamlit run app.py
    ```

## 📋 Estrutura Legal das Fórmulas (Excel)

A planilha gerada utiliza a seguinte lógica para encontrar o valor devido:

```excel
=(Base_Ano * (1,15 ^ Indice_Classe)) + (Base_Ano * 0,05 * Indice_Nivel)

# multi-faturas

O **multi-faturas** é um script modular em Python para extração, transformação e consolidação de faturas de cartão de crédito e extratos bancários em PDF.
O objetivo final é gerar um único arquivo CSV padronizado, otimizado para importação direta em planilhas de acompanhamento financeiro e dashboards de investimentos.

---

## Estrutura do projeto

```
multi-faturas/
├── src/
│   ├── __init__.py
│   ├── main.py              # Ponto de entrada do CLI
│   ├── extractor.py         # Gerenciador de leitura de PDFs
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base_parser.py           # Classe abstrata (Strategy)
│   │   └── template_bank_parser.py  # Exemplo de implementação
│   └── merger.py      # Mescla os dados e exporta para CSV
├── tests/
├── data/
│   ├── input/   # Coloque aqui os PDFs (ignorado no git)
│   └── output/  # CSV consolidado gerado aqui (ignorado no git)
├── .github/workflows/python-app.yml
├── .gitignore
├── requirements.txt
└── README.md
```

## Schema do CSV de saída

| Coluna                   | Tipo    | Descrição                                   |
|--------------------------|---------|---------------------------------------------|
| Data                     | string  | Formato `DD/MM/YYYY`                        |
| Banco/Origem             | string  | Ex.: `"Nubank"`, `"Itaú"`                   |
| Descrição da Transação   | string  | Texto descritivo extraído do PDF            |
| Valor                    | float   | Valor da transação (negativo = débito)      |
| Categoria                | string  | Vazio por padrão; para preenchimento futuro |

## Instalação

```bash
uv sync
```

## Uso

```bash
# Estrutura esperada:
# root/
#   BB/
#     fatura_*.pdf
#   Itau/
#     fatura_*.pdf
#   output/

# O nome da pasta pode variar (ex.: BB, banco_do_brasil, BancoDoBrasil).
# Ele sera normalizado para o id canonico do banco (bb, nubank, itau, etc).

uv run src.main --root caminho/para/root
```

## Saidas

- Consolidado (todos os bancos): `output/faturas_consolidadas_<inicio>_<fim>.csv`
- Por banco: `output/<BANCO>/fatura_<banco>_<cartao>_<periodo>.csv`

Os periodos usam abreviacao de mes em PT-BR (ex.: `jan-2024`, `fev-2024`).
Se o numero do cartao nao for encontrado no PDF, o nome usa um contador por banco/periodo.

## Senha de PDF (CPF)

Alguns PDFs de bancos usam o CPF como senha. Para tentar desbloquear automaticamente,
crie um arquivo `.env` na raiz com:

```bash
CPF=12345678900
```

O parser tenta, nesta ordem: 6 primeiros digitos, 5 primeiros digitos e o CPF completo.

## Variaveis de ambiente

- ROOT_DATA_DIR: diretório raiz com as pastas dos bancos (default: .)

## Adicionando um novo banco

1. Copie `src/parsers/template_bank_parser.py` para `src/parsers/meu_banco_parser.py`.
2. Implemente o método `parse()` com a lógica de extração específica do banco.
3. Registre o parser em `PARSER_REGISTRY` dentro de `src/main.py`.

## Testes

```bash
pytest tests/ -v
```

## CI/CD

O workflow `.github/workflows/python-app.yml` executa automaticamente o **flake8** (linting)
e o **pytest** (testes) a cada push ou pull request na branch `main`.

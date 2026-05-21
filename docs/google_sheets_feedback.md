# Feedback no Google Sheets

O formulário de feedback salva sempre em `data/feedback.csv`.

Quando a integração abaixo estiver configurada, cada resposta também será enviada
para uma aba do Google Sheets.

## Configuração recomendada

1. Crie uma planilha no Google Sheets.
2. Crie uma Service Account no Google Cloud.
3. Baixe o JSON da Service Account.
4. Compartilhe a planilha com o e-mail da Service Account como editor.
5. Salve o JSON no servidor em:

```text
/opt/PHOSDash/google_service_account.json
```

6. Configure os secrets do Streamlit em `/opt/PHOSDash/.streamlit/secrets.toml`:

```toml
[google_sheets]
sheet_id = "ID_DA_PLANILHA"
worksheet = "Feedback"
service_account_file = "/opt/PHOSDash/google_service_account.json"
```

O `sheet_id` fica na URL da planilha:

```text
https://docs.google.com/spreadsheets/d/SHEET_ID/edit
```

## Comportamento

- Se o Google Sheets estiver configurado, o envio grava no CSV e na planilha.
- Se o Google Sheets falhar, o CSV local continua recebendo a resposta.
- `data/feedback.csv`, backups e arquivos de credencial ficam fora do Git.

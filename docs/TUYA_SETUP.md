# Configuração Tuya e TinyTuya — Elgin Smart Color A70

Este guia explica como obter **Device ID, IP, versão do protocolo e Local Key** para utilizar o [Elgin Smart Local](../README.md) sem depender da nuvem durante o controle cotidiano. A configuração inicial exige acesso autorizado à conta/dispositivos Tuya. As telas e serviços podem mudar.

> **Segurança:** o repositório é público. Nunca publique Access Secret, Local Keys, tokens, arquivos `devices.json`, `tinytuya.json`, `tuya-raw.json` ou `snapshot.json`, nem capturas que revelem credenciais. O `.gitignore` não remove segredos já commitados.

## 1. Preparar a rede e os dispositivos

1. Pareie as lâmpadas no aplicativo **Elgin Smart**, confirme que funcionam normalmente e mantenha a integração existente com Google Home.
2. Conecte o computador à mesma LAN roteável. **Não é necessário usar a mesma banda Wi-Fi:** uma lâmpada em 2,4 GHz pode conversar com um computador em 6 GHz quando o mesh não isola os clientes.
3. Não redefina as lâmpadas, não altere o firmware e não as transfira de conta para realizar este procedimento.

## 2. Criar um projeto na Tuya Developer Platform

1. Acesse [Tuya Developer Platform](https://platform.tuya.com/) e faça login.
2. Entre em **Cloud → Cloud Development → My Cloud Projects → Create Cloud Project**.
3. Exemplo de preenchimento usado nesta instalação:
   - **Project Name:** `Elgin Smart Local`
   - **Description:** `Local RGB lighting control using TinyTuya`
   - **Industry:** `Smart Home` (ou equivalente)
   - **Development Method:** `Smart Home`
   - **Data Center:** `Western America Data Center` **somente se corresponder à região da conta**. Foi a região utilizada neste caso, não uma regra universal para o Brasil.
4. Na etapa de APIs, mantenha as permissões necessárias: **IoT Core**, **Authorization Token Management** e **Smart Home Basic Service**. Serviços adicionais de dashboard e cenas depreciadas não são necessários para este fluxo.
5. Não contrate planos pagos nem aceite upgrades sem avaliar custos e limites. Disponibilidade, nomes e condições de avaliação podem mudar.

## 3. Vincular a conta e verificar os dispositivos

1. No projeto, abra **Devices → Link App Account → Add App Account**.
2. Gere o QR Code e escaneie com o aplicativo compatível indicado pela Tuya (normalmente **Smart Life**). **O Elgin Smart pode reconhecer o QR Code sem concluir a autorização.**
3. Atualize a tabela: a conta deve aparecer em **Link App Account** e as lâmpadas em **All Devices** com seus respectivos IDs.
4. Se o QR Code expirar imediatamente e continuar mostrando **0 accounts**, **não considere a vinculação concluída**. Gere um QR Code novo uma vez, confirme a região do projeto e a compatibilidade do aplicativo. Não redefina dispositivos nem assuma que contas Elgin Smart e Smart Life compartilham login.
5. O critério de sucesso é ver os dispositivos associados ao projeto, não apenas a mensagem no celular. Neste caso, os três dispositivos foram posteriormente exibidos em **All Devices**; o procedimento exato que resolveu a vinculação não foi registrado.

## 4. Obter as chaves com TinyTuya

No Pop!_OS 24.04:

```bash
mkdir -p ~/AI/elgin-smart-setup
cd ~/AI/elgin-smart-setup
python3 -m venv .venv
source .venv/bin/activate
python -m pip install tinytuya
python -m tinytuya wizard
```

No assistente, informe:
- **API Key:** `Access ID / Client ID`, em **Cloud Project → Overview → Authorization Key**.
- **API Secret:** `Access Secret / Client Secret`, na mesma tela.
- **API Region:** para **Western America**, `us`; use outra região quando aplicável.
- Se solicitado, informe o **Device ID** associado ao projeto.
- Em **Poll local devices? (Y/n)**, responda `y`.

O wizard pode criar `devices.json`, `tinytuya.json`, `tuya-raw.json` e `snapshot.json`. Mantenha esses arquivos em diretório privado, fora de commits e compartilhamentos. O polling bem-sucedido deve mostrar o estado DPS de cada lâmpada; no modelo A70 validado, DPS 20–24 incluem energia, modo, brilho branco, temperatura e HSV.

Para uma verificação sem revelar as chaves:

```bash
python - <<'PY'
import json
with open("devices.json", encoding="utf-8") as f:
    data = json.load(f)
items = data if isinstance(data, list) else data.get("devices", [])
for d in items:
    print({"name": d.get("name"), "ip": d.get("ip"),
           "version": d.get("version"), "has_key": bool(d.get("key"))})
PY
```

A descoberta local isolada pode ser testada com `python -m tinytuya scan`. **Descoberta UDP não prova autenticação**; para validar o controle, o polling deve retornar DPS sem erro.

## 5. Instalar as credenciais no aplicativo COSMIC

Consulte também [INSTALL.md](INSTALL.md). Para instalação via pacote `.deb`, crie a configuração privada:

```bash
mkdir -p ~/.config/elgin-smart-local
chmod 700 ~/.config/elgin-smart-local
cp ~/AI/elgin-smart-setup/devices.json ~/.config/elgin-smart-local/devices.json
chmod 600 ~/.config/elgin-smart-local/devices.json
```

Confira localmente se os campos `name`, `id`, `ip`, `key` e `version` seguem o [exemplo](../devices.example.json), sem copiar valores secretos para mensagens ou issues. Os IPs podem mudar por DHCP; reservas DHCP no roteador podem ajudar, mas são opcionais.

Abra **Elgin Smart Local** pelo launcher do COSMIC. O app usa as Local Keys para comandos pela LAN; **não precisa consultar a Tuya Cloud para cada alteração de brilho, saturação ou cor**. As chaves podem deixar de funcionar após novo pareamento ou determinadas mudanças de configuração.

## Solução de problemas

| Sintoma | Verificação |
| --- | --- |
| Tuya Developer Platform não abre | Testar `https://platform.tuya.com/` ou `https://developer.tuya.com/`; verificar DNS/rede |
| QR Code expira e `0 accounts` | Não vinculado; verificar app compatível, região e gerar novo QR |
| Dispositivos ausentes em All Devices | Confirmar associação da conta e data center |
| Scan encontra IP, mas polling falha | Conferir Local Key, versão 3.4/3.5, conectividade e possível mudança de IP |
| Computador 6 GHz, lâmpadas 2,4 GHz | Verificar isolamento de clientes, VLANs e roteamento; frequência diferente não é impedimento |
| Brilho mínimo diferente do esperado | Ver [README](../README.md#precisão-e-comportamento-dos-controles): brilho branco DPS22 e valor HSV são controles distintos |

Para documentação de referência, consulte o [TinyTuya](https://github.com/jasonacox/tinytuya). Este tutorial descreve o fluxo usado neste projeto, sem prometer compatibilidade com todos os firmwares Elgin.

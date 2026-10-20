# Instalação — Pop!_OS 24.04

Os pacotes da versão 1.0.0 são destinados a **amd64/x86-64**, COSMIC e **Python 3.12** do Pop!_OS 24.04. Não exigem compilação nem pip. TinyTuya e suas dependências Python estão incluídos; bibliotecas padrão do sistema continuam necessárias.

## Verificar os downloads

Baixe o pacote desejado e `SHA256SUMS` na [release](https://github.com/Arthurregiani/elgin-smart-local/releases/latest). Na mesma pasta:

```bash
sha256sum --check --ignore-missing SHA256SUMS
```

O pacote baixado deve retornar `OK`. SHA-256 verifica a integridade do download; os arquivos não são assinados digitalmente.

## Instalação do sistema (.deb)

```bash
sudo apt install ./elgin-smart-local_1.0.0_amd64.deb
```

O apt pode instalar dependências do sistema que estejam faltando. O pacote não possui scripts que iniciem processos, serviços ou modifiquem configurações de usuários.

Crie o arquivo de dispositivos e substitua todos os valores fictícios:

```bash
mkdir -p ~/.config/elgin-smart-local
chmod 700 ~/.config/elgin-smart-local
cp /usr/share/doc/elgin-smart-local/devices.example.json ~/.config/elgin-smart-local/devices.json
chmod 600 ~/.config/elgin-smart-local/devices.json
```

Se já existir um `devices.json`, preserve-o em vez de executar o comando de cópia novamente. Edite o arquivo com um editor de texto. Depois abra **Elgin Smart Local** no launcher, ou execute `/usr/bin/elgin-smart-local`.

Para atualizar, instale o novo `.deb` com o mesmo comando apt. Para remover:

```bash
sudo apt remove elgin-smart-local
```

Configurações em `~/.config/elgin-smart-local` permanecem no computador.

## Instalação por usuário (.tar.gz)

```bash
tar -xzf elgin-smart-local-1.0.0-popos24.04-amd64.tar.gz
cd elgin-smart-local-1.0.0-popos24.04-amd64
./install.sh
```

O instalador copia o aplicativo para `~/.local/lib/elgin-smart-local`, cria o comando em `~/.local/bin` e instala o launcher e o ícone em `~/.local/share`. Não usa sudo, não acessa a rede e não copia credenciais. A pasta extraída pode ser removida depois da instalação.

Um modelo é disponibilizado no diretório de configuração. Se não existir uma configuração real, copie-o e edite os dados:

```bash
cp ~/.config/elgin-smart-local/devices.example.json ~/.config/elgin-smart-local/devices.json
chmod 600 ~/.config/elgin-smart-local/devices.json
```

Abra pelo launcher ou execute `~/.local/bin/elgin-smart-local`. Para remover apenas essa instalação:

```bash
~/.local/lib/elgin-smart-local/uninstall.sh
```

A configuração e os presets permanecem no diretório de configuração.

## Arquivos e caminhos

| Finalidade | Caminho padrão |
| --- | --- |
| Configuração de lâmpadas | `~/.config/elgin-smart-local/devices.json` |
| Presets | `~/.config/elgin-smart-local/presets.json` |
| Executável e dependências do .deb | `/usr/lib/elgin-smart-local/` |
| Executável e dependências por usuário | `~/.local/lib/elgin-smart-local/` |

O aplicativo respeita `XDG_CONFIG_HOME`. `ELGIN_DEVICES_FILE` permite indicar outro arquivo privado de dispositivos. Para compatibilidade com instalações por fontes anteriores, um `devices.json` existente no diretório do aplicativo também é reconhecido. Nenhum desses arquivos reais é fornecido pela release.

Se houver uma instalação por usuário e outra do sistema, o launcher do usuário pode ter precedência. Prefira manter apenas um método de instalação. Ao migrar de uma instalação por fontes, preserve o arquivo de dispositivos, copie-o para o diretório XDG se necessário e só então remova a instalação antiga.

## Solução de problemas

- **Solicitação para configurar as lâmpadas:** confirme o caminho, o formato JSON e os campos `name`, `id`, `key`, `ip` e `version`. O aplicativo não descobre Local Keys automaticamente.
- **Falha LAN:** confirme que a lâmpada está energizada, o IP está correto, o protocolo corresponde ao firmware e a rede permite comunicação entre dispositivos. Evite vários controladores LAN simultâneos.
- **Falha ao iniciar TinyTuya:** confirme Python 3.12 e a integridade do pacote. Não misture arquivos de releases diferentes.
- **Nenhum launcher após instalação por usuário:** execute `~/.local/bin/elgin-smart-local` e verifique se o arquivo `.desktop` existe em `~/.local/share/applications`.
- **Sem emissão ao ajustar brilho:** liga/desliga é independente. Confirme que a lâmpada está ligada; V=0 no modo colorido não equivale ao desligamento pelo DPS 20.

O fechamento normal encerra o auxiliar. Ele também recebe um sinal de encerramento se a interface morrer inesperadamente. Não há daemon para habilitar no boot.

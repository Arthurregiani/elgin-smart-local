# Elgin Smart Local

Aplicativo desktop nativo para controlar lâmpadas **Elgin Smart Color A70** pela rede local, com interface **COSMIC**, Rust/libcosmic e TinyTuya. Brilho, saturação e tonalidade têm controles independentes, com a resolução nativa dos dispositivos compatíveis.

**[Baixar a versão para Pop!_OS 24.04](https://github.com/Arthurregiani/elgin-smart-local/releases/latest)** · [Instalação e configuração](docs/INSTALL.md) · [Arquitetura](docs/TECHNICAL.md)

## Recursos

- Seleção individual ou múltipla de lâmpadas.
- Roda de tonalidade, campos numéricos e entrada RGB/hexadecimal.
- Brilho colorido e saturação em passos de **0,1%**, Hue em passos de **1°**.
- Modo branco com brilho e temperatura independentes; preservação dos ajustes de cada modo.
- Liga/desliga separado dos valores de cor e brilho.
- Presets locais e indicação de conexão, sincronização e divergências.
- Consolidação de comandos durante o movimento dos sliders e leitura do estado após alterações.

A comunicação de iluminação acontece diretamente na LAN. Não exige navegador, Docker, Home Assistant, servidor HTTP ou serviço permanente. O auxiliar TinyTuya é iniciado com a janela e encerrado junto com o aplicativo.

## Compatibilidade

| Item | Suporte nesta versão |
| --- | --- |
| Sistema dos pacotes compilados | Pop!_OS 24.04 com COSMIC |
| Arquitetura | amd64 / x86-64 |
| Python do sistema | 3.12 |
| Dispositivos validados | Elgin Smart Color A70, protocolos Tuya 3.4 e 3.5 |
| Esquema de iluminação | DPS 20–24; HSV no formato `HHHHSSSSVVVV` |

Outros modelos e firmwares podem ter limites ou mapeamentos diferentes e não estão validados. Os pacotes não são destinados a ARM nem a versões anteriores do Pop!_OS.

## Instalação rápida

Baixe o arquivo `.deb` na página de [releases](https://github.com/Arthurregiani/elgin-smart-local/releases/latest) e execute na pasta do download:

```bash
sudo apt install ./elgin-smart-local_1.0.0_amd64.deb
```

O pacote contém o aplicativo compilado, TinyTuya e suas dependências Python. **Não é necessário instalar Rust, criar um ambiente virtual ou executar pip.** O apt pode obter bibliotecas do sistema que estejam faltando.

Para instalar somente no usuário, sem sudo, use o `.tar.gz` da mesma release. Instruções e verificação dos checksums estão no [guia de instalação](docs/INSTALL.md).

## Configurar as lâmpadas

Nenhum pacote inclui dispositivos reais ou credenciais. Antes de usar, crie uma configuração privada:

```bash
mkdir -p ~/.config/elgin-smart-local
chmod 700 ~/.config/elgin-smart-local
cp /usr/share/doc/elgin-smart-local/devices.example.json \
   ~/.config/elgin-smart-local/devices.json
chmod 600 ~/.config/elgin-smart-local/devices.json
```

Edite o arquivo com o nome, Device ID, IP local, Local Key e versão do protocolo de cada lâmpada. O modelo contém apenas valores fictícios. A versão do protocolo deve corresponder ao dispositivo, por exemplo `3.4` ou `3.5`.

Os IDs e Local Keys precisam estar disponíveis antes do uso. O aplicativo não faz pareamento nem extrai chaves. Siga o **[tutorial completo de configuração da Tuya Developer Platform e TinyTuya](docs/TUYA_SETUP.md)** para criar o projeto, vincular a conta, recuperar as chaves e solucionar problemas de QR Code. Mantenha o computador e as lâmpadas em uma rede que permita comunicação entre eles.

Depois, abra **Elgin Smart Local** no launcher do COSMIC. Para a instalação por usuário, o modelo e os caminhos estão descritos no [guia](docs/INSTALL.md#instalação-por-usuário-targz).

## Precisão e comportamento dos controles

| Controle | Comportamento nos dispositivos validados |
| --- | --- |
| Brilho colorido | V=0–1000, equivalente a 0–100%; menor valor positivo V=1 (0,1%) |
| Saturação | S=0–1000; S=0 produz uma cor dessaturada sem modificar V |
| Tonalidade | H=0–360; alterar Hue preserva S e V |
| Brilho branco | DPS22=10–1000; mínimo de 1,0%, em passos de 0,1% |
| Temperatura | DPS23=0–1000, exibido como quente → frio; sem conversão calibrada para kelvin |

No branco, **0% desliga** e o último brilho permanece guardado; valores positivos abaixo de 1% são normalizados para o mínimo suportado. No colorido, **V=0 é enviado literalmente** e não equivale ao comando liga/desliga. Ajustar valores não liga automaticamente uma lâmpada desligada.

Pressione **Enter** para confirmar um campo numérico. RGB/HEX define H, S e V juntos; use o anel ou o campo Hue quando quiser preservar saturação e brilho. Em seleção múltipla, os valores exibidos vêm da primeira lâmpada selecionada com estado conhecido, mas os outros componentes de cada lâmpada são preservados em alterações isoladas.

**Aguardando confirmação** não significa que o ajuste foi aplicado. O cartão de cada lâmpada mostra o estado retornado. Use **Sincronizar estado real** para reler os dispositivos; esse botão não repete escritas que falharam.

A validação confirma valores retornados pelo firmware, não luminosidade medida. Não há garantia de que cada passo numérico produza uma diferença perceptível, de linearidade luminosa ou de fidelidade colorimétrica. A prévia RGB é aproximada. Veja os [resultados e limitações](docs/VALIDATION.md).

## Privacidade

- Credenciais ficam no arquivo local de configuração, fora do controle de versão.
- Local Keys não são enviadas à interface, aos presets ou aos logs do aplicativo.
- Releases incluem apenas código, executável, dependências, ícone, documentação e configuração de exemplo fictícia.
- O aplicativo não altera firmware, pareamento, conta Tuya, integração Google Home, cenas ou temporizadores.
- Controladores externos podem alterar o estado; o aplicativo relê os dispositivos periodicamente e antes das alterações.

## Compilar a partir do código

São necessários Rust **1.93 ou superior**, Cargo, Python 3.12/venv e as dependências de desenvolvimento do libcosmic para Linux. Em Pop!_OS 24.04:

```bash
sudo apt install build-essential pkg-config libxkbcommon-dev libwayland-dev python3-venv
git clone https://github.com/Arthurregiani/elgin-smart-local.git
cd elgin-smart-local
./scripts/install.sh
```

Configure as lâmpadas no caminho XDG descrito acima. O instalador de fontes compila o executável e mantém uma referência ao ambiente virtual do checkout; conserve esse diretório. A release compilada oferece instalação independente do checkout.

## Testes e contribuição

```bash
.venv/bin/python -m unittest discover -s tests -v
cargo test --locked --manifest-path native/Cargo.toml
```

Os testes automatizados usam dispositivos simulados. Testes físicos são separados, alteram temporariamente a iluminação e tentam restaurar o estado anterior:

```bash
.venv/bin/python scripts/verify_hardware.py --ip IP_DA_LAMPADA
```

Registros e capturas em `evidence/` são locais e não são publicados. Ao abrir uma issue, informe sistema, versão e comportamento observado, removendo Local Keys, IDs, IPs e dados pessoais de qualquer diagnóstico. Para gerar os pacotes, consulte [packaging/README.md](packaging/README.md).

O aplicativo utiliza [libcosmic](https://github.com/pop-os/libcosmic) e [TinyTuya](https://github.com/jasonacox/tinytuya). Os pacotes acompanham os avisos e licenças das dependências de terceiros.

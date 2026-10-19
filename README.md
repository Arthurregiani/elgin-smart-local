# Elgin Smart Local — COSMIC

Aplicativo desktop nativo Rust/libcosmic para lâmpadas Elgin Smart Color A70, via TinyTuya na LAN. Sem navegador, HTTP, Docker, Home Assistant ou daemon. Abre pelo launcher **Elgin Smart Local**.

## Instalar / atualizar

```bash
git clone https://github.com/Arthurregiani/elgin-smart-local.git
cd elgin-smart-local
cp devices.example.json devices.json
# Edite devices.json localmente com seus IDs, IPs, versões e Local Keys.
chmod 600 devices.json
./scripts/install.sh
```

Se você já usa a instalação original em `~/AI/elgin-smart`, basta executar `./scripts/install.sh` nesse diretório; preserve seu `devices.json`. O exemplo contém somente valores fictícios.

Requer Rust/Cargo, Python 3 com venv e as bibliotecas de desenvolvimento Wayland/XKB do sistema. O instalador não usa sudo. Compila a versão fixada de libcosmic e instala executável, ícone e `.desktop` em `~/.local`. Reutiliza `.venv` e mantém um link para o `devices.json` original; conserve o diretório do projeto. TinyTuya é fixado em 1.20.0. O ambiente existente de FastAPI é preservado, mas não é iniciado pelo aplicativo.

Executar diretamente:

```bash
~/.local/bin/elgin-smart-local
```

## Usar

1. Selecione uma ou mais lâmpadas. A interface só habilita controles após conhecer o estado de ao menos uma selecionada. Dispositivos sem estado conhecido são ignorados até reconectar.
2. Escolha **Colorido** ou **Branco**. Mudar de modo preserva os ajustes de ambos. Os botões **Ligar/Desligar** controlam a alimentação luminosa separadamente.
3. No colorido, use a roda para Hue; saturação e brilho têm controles próprios. Campos numéricos aceitam vírgula ou ponto decimal; **Enter confirma**. Passos: 1° em Hue, 0,1% em S/V.
4. Branco: 0% desliga; o mínimo confirmado é 1,0%, DPS22=10. Valores positivos menores são normalizados para 1,0%. O último brilho fica guardado quando desligada. Ajustar o brilho não liga automaticamente uma lâmpada desligada.
5. Colorido: 0% envia V=0; 0,1% envia V=1. O liga/desliga permanece independente. Para tentar a menor emissão colorida positiva, use 0,1% e ligue a lâmpada.
6. HEX e RGB definem os três componentes HSV juntos. Para preservar saturação e brilho, use Hue. A prévia representa RGB aproximado; não é uma medição da lâmpada.
7. Temperatura usa 0–100% de quente a frio, com passo de 0,1%. Não se inventa um intervalo em kelvin.
8. Salve presets locais com nome. Na seleção múltipla, os valores exibidos vêm da primeira lâmpada selecionada com estado conhecido; um ajuste isolado preserva os outros componentes de cada lâmpada. Presets aplicam o conjunto de ajustes, preservando liga/desliga.

Os cartões mostram o estado efetivamente retornado. **Aguardando confirmação** não significa sucesso. Uma divergência exibe o solicitado e o recebido; falhas de rede pedem sincronização. **Sincronizar estado real** relê as selecionadas; não repete uma escrita falha. Para tentar novamente uma alteração, ajuste o controle outra vez. Também há consulta automática a cada 15 segundos.

## Privacidade e preservação

- Local Keys nunca são enviadas à interface, a logs, a presets ou a pacotes de distribuição.
- `devices.json`, `tinytuya.json`, `tuya-raw.json`, `snapshot.json`, backups e ambiente virtual estão ignorados pelo Git; arquivos sensíveis existentes foram restringidos a modo 0600.
- Nenhuma mudança de firmware, pareamento, conta Tuya, Google Home, cenas, timers ou memória de inicialização.
- O auxiliar existe apenas durante o aplicativo. Ao fechar, conclui a última intenção pendente dentro de uma espera limitada e encerra; em falha da interface, recebe sinal de morte do processo pai.
- Não use simultaneamente o painel antigo ou outro controlador LAN durante testes. Google Home e o aplicativo oficial podem alterar o estado externamente; a próxima sincronização reflete essa mudança.

## Testes

Sem alterar lâmpadas:

```bash
.venv/bin/python -m unittest discover -s tests -v
cargo test --locked --manifest-path native/Cargo.toml
```

Renderização real da janela, capturas e fechamento automático em cerca de 13 segundos, somente leituras LAN:

```bash
mkdir -p evidence
ELGIN_SMOKE=1 native/target/release/elgin-smart-local
```

**Testes físicos alteram a iluminação**, uma lâmpada por vez, salvam os estados antes da primeira escrita e restauram no final. Execute somente quando puder tolerar a mudança breve:

```bash
.venv/bin/python scripts/verify_hardware.py --all
```

Evidências são geradas localmente em `evidence/` e não são publicadas; detalhes e limites em [docs/TECHNICAL.md](docs/TECHNICAL.md) e resultados em [docs/VALIDATION.md](docs/VALIDATION.md). A granularidade foi confirmada por leitura dos DPS, sem medição fotométrica.

## Arquivos e remoção

- Fontes: `native/`, `bridge/`, `tests/`, `scripts/`.
- Configuração de dispositivos: `devices.json` na raiz do seu checkout; nunca versionar. Na instalação original: `~/AI/elgin-smart/devices.json`.
- Presets: `${XDG_CONFIG_HOME:-~/.config}/elgin-smart-local/presets.json`.
- Instalação: `~/.local/lib/elgin-smart-local`, wrapper em `~/.local/bin`, ícone e launcher em `~/.local/share`.
- Na instalação original, os arquivos do painel antigo e seus backups são preservados localmente, fora do repositório.

Para remover apenas o aplicativo: `./scripts/uninstall.sh`. Projeto, credenciais e presets permanecem. Somente na instalação original, que preserva os arquivos legados, para voltar temporariamente ao painel antigo: `.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8765`; encerre o aplicativo nativo antes e termine o servidor quando não precisar dele.

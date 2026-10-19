# Validação executada — 19/10/2026

Este documento resume uma validação local. Os arquivos de `evidence/` citados abaixo contêm dados da instalação original e não são publicados no repositório. Os nomes A, B e C são identificadores anônimos.

## Resultado

Aplicativo compilado e instalado no usuário local, com Rust/libcosmic, TinyTuya 1.20.0, ícone e arquivo `.desktop`. Execução gráfica real no COSMIC confirmada. Não depende do painel web antigo, cujo processo foi encerrado; a porta 8765 ficou sem listener.

## Testes automatizados

- **23 testes Python aprovados**: limites e todos os 991 níveis positivos de branco; HSV em valores extremos; independência H/S/V; zero branco versus desligamento; temperatura; modos; validação; detecção de estado parcial e divergência; consolidação de 10.000 entradas; ordenação liga/desliga após brilho zero; fechamento de sockets em sucesso/falha; escolha 3.4/3.5; correção do modo implícito do firmware; controle de taxa; preservação do último pedido; drenagem ao fechar; erro sanitizado sem repetição infinita; isolamento entre dispositivos; preservação de brilho alterado externamente.
- **5 testes Rust aprovados**: cores primárias, ciclo Hue 0/360, cinza preservando Hue, HEX inválido, precisão e ida/volta RGB/HSV em uma grade de 4.096 cores (erro tolerado de até 2 níveis RGB devido à quantização de Hue).
- `cargo clippy -- -D warnings`: aprovado.
- Build release com `Cargo.lock`: aprovado.
- `desktop-file-validate`: aprovado após usar apenas a categoria principal Utility.
- Busca literal das Local Keys em fontes, documentação, evidências textuais e executável: nenhuma ocorrência. Não se imprime a chave durante essa verificação.

Os resultados completos estão em `evidence/tests-python.txt`, `evidence/tests-rust.txt` e `evidence/clippy.txt`.

## Lâmpadas reais

| Dispositivo | Protocolo | Ajustes pequenos e leitura completa | Estado restaurado |
| --- | --- | --- | --- |
| Lâmpada A | 3.4 | 9 verificações aprovadas | Sim |
| Lâmpada B | 3.5 | 9 verificações aprovadas | Sim |
| Lâmpada C | 3.4 | 9 verificações aprovadas | Sim, selecionando o modo final separadamente |

Em todas, o firmware confirmou V=0, V=1, V=2, S=0 e S=1, bem como mudança só de Hue e alternância dos modos. Uma aplicação adicional de preset misto na lâmpada C confirmou a correção de modo e a restauração completa; evidência em `evidence/preset-mode.json`. No ensaio inicial da lâmpada A, DPS22 abaixo de 10 não foi aceito. Veja os arquivos `evidence/acceptance-*.json` e `physical-porta.json`.

## Janela e ciclo de vida

A versão instalada abriu via `~/.local/bin/elgin-smart-local`, leu os três dispositivos, renderizou os modos branco e colorido e fechou automaticamente pelo fluxo de encerramento da aplicação. Código de saída 0, sem mensagens de erro. Capturas reais foram abertas e inspecionadas: `evidence/ui-3.png` (branco) e `evidence/ui-7.png` (colorido). O teste de redimensionamento foi solicitado, mas o compositor manteve o tamanho da janela nessa sessão; `ui-11.png` não comprova uma janela estreita. O código reorganiza o conteúdo abaixo de 900 px e oferece rolagem; a interação manual em janela estreita e a navegação completa por leitor de tela não foram certificadas.

Uma falha na recriação do canal de eventos durante o fechamento apareceu no primeiro ensaio, foi corrigida e o fechamento foi repetido com sucesso. Não há auxiliar Python executando depois do fechamento normal. A abertura de uma segunda instância ativou a existente e terminou com código 0, mantendo exatamente um auxiliar; o encerramento da primeira também retornou 0 e não deixou filhos. Evidência: `evidence/single-instance.json`.

Um ensaio separado encerrou a interface com SIGKILL. O sinal de morte do pai encerrou o TinyTuya e nenhum auxiliar permaneceu executando. A evidência `evidence/lifecycle.json` contém a amostra de seis segundos em repouso:

| Processo | RSS aproximado | CPU, percentual de um núcleo |
| --- | --- | --- |
| Interface | 40,2 MiB | 0,67% |
| TinyTuya | 35,4 MiB | 0,00% |

É uma medição curta de repouso, não um benchmark nem um limite garantido; não inclui o compositor do desktop.

## Limites da conclusão

A confirmação física foi feita pelo estado LAN dos dispositivos. Não houve medição fotométrica ou colorimétrica: não foi determinado se cada passo numérico produz mudança perceptível, nem a menor emissão visível real. O aplicativo expõe todos os valores nativos confirmados, incluindo o mínimo colorido positivo V=1, sem impor o mínimo branco ao modo colorido.

O transporte Rust alternativo foi investigado, mas não validado nem incorporado. Nenhuma operação de cloud, firmware, pareamento ou integração Google Home foi executada.

A leitura final em `evidence/final-state.json` confirmou as três lâmpadas iguais aos estados anteriores aos ensaios.

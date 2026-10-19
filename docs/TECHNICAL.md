# Investigação e arquitetura — 19/10/2026

Este documento resume uma validação local. Os arquivos de `evidence/` citados abaixo contêm dados da instalação original e não são publicados no repositório. Os nomes A, B e C são identificadores anônimos.

## Diagnóstico do projeto recebido

O FastAPI em `app.py` forçava `21=white` em qualquer ajuste de brilho e temperatura. O seletor RGB convertia RGB de 8 bits em HSV e sobrescrevia H, S e V simultaneamente. Não existia controle independente de saturação nem do V colorido. O limite de 1% da interface e o arredondamento em percentuais inteiros também eliminavam resolução. O uso de `max(10, ...)` era compatível com o mínimo branco anunciado, mas não deveria ser aplicado ao V colorido.

Os três registros em `devices.json` anunciam o mesmo esquema de iluminação. Leitura LAN confirmou os DPS reais, tanto em 3.4 quanto 3.5:

| DPS | Função | Domínio |
| --- | --- | --- |
| 20 | Liga/desliga | booleano |
| 21 | Modo | white / colour; scene e music somente observados, nunca programados pelo app |
| 22 | Brilho branco | 10–1000, passo 1 |
| 23 | Temperatura | 0–1000, passo 1; sem calibração Kelvin disponível |
| 24 | Cor HSV | 12 caracteres hexadecimais: HHHHSSSSVVVV; H=0–360, S/V=0–1000 |

A escala percentual corresponde ao número nativo dividido por 10. A faixa branca efetiva começa em 1,0%. A interface aceita 0 para desligar pelo DPS 20; valores positivos abaixo de 1% são quantizados ao mínimo físico anunciado, exibido como 1,0%. Os botões liga/desliga são separados e preservam os ajustes. Na cor, V=0 é enviado literalmente; V=1 é 0,1%. Um V=0 não equivale a DPS20=false. Hue 360 é equivalente ao vermelho de 0 na prévia RGB, sem reduzir o domínio do DPS.

## Evidência física e limitações

`evidence/physical-porta.json` registra a investigação inicial. Escritas 9, 1 e 0 em DPS22 mantiveram o retorno em 10. A sessão persistente entregou notificações parciais de DPS24; estas não foram usadas como comprovação de estado completo. A restauração final foi confirmada por conexão nova.

`evidence/acceptance-*.json` contém nove alterações pequenas por lâmpada, executadas sequencialmente: mínimo branco, ligar, V=1/S=0, S=1, mudança só de H, V=0, V=2 e alternância dos modos. As leituras completas confirmaram os valores. As três lâmpadas foram restauradas aos estados originais.

Um comportamento real da A70 exige cuidado: atualizar os DPS de branco no mesmo pacote que `21=colour` pode deixar o modo em branco. A aplicação lê o resultado, restabelece o modo solicitado em comando separado se necessário e lê novamente. A restauração da lâmpada C identificou esse comportamento; a correção posterior foi confirmada.

Esta é validação de protocolo, granularidade e estado retornado pelo firmware. Não foi usado luxímetro/fotômetro: não se afirma linearidade luminosa, quantidade física de luz, fidelidade espectral, nem que cada passo de 0,1% gere diferença visível. A prévia RGB na tela é aproximada, especialmente em intensidades muito baixas.

## Comunicação e ciclo de vida

- Interface Rust/libcosmic com revisão fixada no Cargo.toml e Cargo.lock versionável.
- Um processo Python/TinyTuya 1.20.0 por instância, comunicação JSONL exclusivamente por pipes. Nenhuma porta HTTP ou serviço em segundo plano.
- Credenciais lidas somente pelo Python, do arquivo existente; a interface recebe nome, IP, versão e estado. Erros vindos da biblioteca são substituídos por mensagens seguras, sem despejo de pacotes ou Local Keys.
- Uma thread por lâmpada. Um dispositivo indisponível não bloqueia os demais nem a interface. A interface envia intenções por canal para uma thread escritora; não executa I/O de rede na thread gráfica.
- Fila limitada a um dicionário pendente por lâmpada. Novos valores substituem só o mesmo campo; alterações independentes sobrevivem à consolidação. O estado completo de referência é individual por dispositivo.
- Intervalo mínimo de 300 ms depois de terminar uma operação. Uma única operação em andamento por lâmpada. Na prática a rede e as leituras podem reduzir mais a frequência. O último valor solicitado é enviado após o movimento terminar.
- Conexões TCP curtas: negociação de versão por TinyTuya; fechamento em `finally` inclusive em erro. Leitura completa em sessão nova evita confundir notificações parciais com estado confirmado. Uma repetição de leitura é permitida; não há repetição infinita de escritas.
- O modo final é verificado. Divergências são exibidas com DPS, valor solicitado e valor retornado. Não há ciclo de correção infinita.
- Consulta de estado a cada 15 segundos, botão de sincronização e nova leitura imediatamente antes de editar componentes HSV, para preservar alterações externas recentes. Nenhuma atualização contínua de sliders parados. Leitura pode conflitar com outro controlador local; o app mostra a falha e permite sincronizar.
- Revisões monotônicas impedem uma confirmação antiga de substituir a edição mais recente na interface. Estado real e solicitação em andamento são distinguíveis.
- Fechamento normal envia `quit`, drena a última intenção e aguarda até cinco segundos no auxiliar. O proprietário aguarda até seis segundos, depois encerra e coleta o filho. EOF inesperado cancela o auxiliar. `PR_SET_PDEATHSIG` encerra-o se a interface morrer; existe verificação da corrida de morte do pai na inicialização.
- libcosmic oferece instância única. Um lock exclusivo adicional no auxiliar evita dois controladores locais deste aplicativo.

## Modos, RGB e presets

Mudar apenas Hue preserva S/V; mudar apenas S preserva H/V; mudar V preserva H/S. A roda é um anel de Hue: não usa a distância ao centro para modificar a saturação. Os valores nativos nunca passam por RGB para o envio; RGB/HEX de oito bits são uma entrada alternativa que define H/S/V juntos. Cinza/preto preserva a tonalidade anterior de cada lâmpada.

Os dois conjuntos de DPS permanecem no dispositivo e são relidos ao abrir. O app não reescreve padrões na inicialização. Presets JSON locais guardam os ajustes de ambos os modos, mas não ligam/desligam ao serem aplicados. A gravação usa arquivo temporário, fsync e rename, com diretório privado. Nenhum preset inclui credenciais. A seleção múltipla altera somente os componentes pedidos, preservando os outros valores individuais.

## Tuya diretamente em Rust

A avaliação consultou as fontes primárias abaixo. `tuya-rs` documenta protocolo 3.3; não atende sozinho os dispositivos 3.4/3.5 deste projeto. `rustuya` anuncia ambos, sendo candidato a uma migração. Não foi instalado nem substituiu TinyTuya nesta entrega: uma migração exige repetir os testes físicos de negociação, leitura, comando, timeout, reconexão e restauração nas três lâmpadas. A interface JSONL permite trocar o transporte sem alterar o modelo de iluminação.

3.4 e 3.5 diferem na sessão e no enquadramento/criptografia de rede; o esquema DPS de iluminação observado é o mesmo. Não é correto tratar 3.5 como 3.4. A versão específica de cada registro é repassada explicitamente ao TinyTuya.

Fontes consultadas em 19/10/2026:

- [libcosmic](https://github.com/pop-os/libcosmic), [template oficial](https://github.com/pop-os/cosmic-app-template).
- [TinyTuya e formatos de lâmpadas](https://github.com/jasonacox/tinytuya), [API](https://github.com/jasonacox/tinytuya/blob/master/API.md).
- [tuya-rs](https://docs.rs/tuya-rs/latest/tuya_rs/).
- [rustuya](https://github.com/3735943886/rustuya).

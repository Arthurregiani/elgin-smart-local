# Construir a release

Execute em Pop!_OS 24.04 / x86-64 com Python 3.12, Rust >=1.93, Cargo e `dpkg-deb`. O checkout precisa ter um ambiente `.venv` com pip; não são necessários dispositivos reais.

```bash
python3 scripts/build_release.py
```

A saída fica em `build/release/` (ignorada pelo Git):

- `elgin-smart-local_1.0.0_amd64.deb`
- `elgin-smart-local-1.0.0-popos24.04-amd64.tar.gz`
- `SHA256SUMS`

O script compila com Cargo.lock e remapeia caminhos de compilação. Monta um payload a partir de uma lista explícita: binário, `bridge/`, configuração fictícia, dependências Python provenientes de wheels oficiais com versões e hashes fixados, avisos de terceiros e documentação. Não copia `.venv`, `devices.json`, backups, configurações ou evidências da máquina.

Os wheels incluem extensões compiladas para CPython 3.12/x86-64. O Python 3.12 é fornecido pelo sistema. Os pacotes não executam pip na instalação ou na inicialização. `BUILD-INFO.json` identifica versão, commit de origem e hashes dos wheels.

Antes de publicar, inspecione o conteúdo dos dois pacotes, execute os testes com o Python empacotado no `PYTHONPATH`, instale o tarball em um HOME temporário, valide a abertura do pacote extraído sem configuração real e confira a ausência de credenciais nos bytes descompactados. Registros de validação devem permanecer fora dos assets.

As dependências de terceiros mantêm suas respectivas licenças. Os avisos Rust estão em `THIRD_PARTY_NOTICES.md` e `licenses/`; os avisos Python acompanham seus diretórios `.dist-info`.

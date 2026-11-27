# 9. Direitos, conteúdo explícito e boas práticas

> Este documento é orientação geral, **não é aconselhamento jurídico**. Em dúvida, consulte seu advogado e a sua distribuidora.

## Direitos sobre a arte
- Anime apenas capas das quais você (ou seu selo/artista) detém ou licenciou os direitos.
- Se a capa foi criada com IA generativa, confira os termos da ferramenta e as exigências da sua distribuidora/Apple quanto a conteúdo gerado e a pessoas reais.
- Os GIFs/exemplos deste repositório usam uma **capa procedural própria** (`examples/demo`, CC0). Não publique capas de terceiros ou inéditas em repositórios públicos sem autorização.

## Conteúdo explícito
- O que classifica uma faixa/álbum como **explícito** na Apple Music é o campo de conteúdo explícito nos **metadados do lançamento** (configurado na distribuidora), não a imagem da capa.
- Segundo as diretrizes do *Motion Album Artwork* (ver [05](05-especificacoes-apple.md)), a arte de motion **não deve exibir** o selo Parental Advisory. `studio.py init --remove-badge` (ou `prepare_cover.py --remove-badge`) apaga o selo da **imagem** e `init` **avisa** quando o detecta.
- Isso **não** altera nenhuma marcação de metadados: mantenha o campo *Explicit* correto no lançamento (na distribuidora).
- Consulte as diretrizes de conteúdo da Apple/distribuidora sobre o que é permitido na arte.

## Acessibilidade
- Sem flashes ou strobing. O validador estima transições de luminância, mas não substitui um teste com ferramenta específica (ex.: *Photosensitive Epilepsy Analysis Tool*).
- Mantenha contraste e legibilidade do texto da capa.

## Boas práticas de entrega
1. Renomeie com o **UPC correto**.
2. Assista aos dois vídeos **inteiros em tela cheia** (recorte por IA e extensão do 3:4).
3. Guarde o `config.json`, a capa limpa e o log de render junto do lançamento (reprodutível).
4. Peça à distribuidora o retorno do validador oficial e anexe aqui como issue se algo novo aparecer.

# 7. Skill e agente de IA (Claude / Copilot)

A pasta [`claude/`](../claude/) contém:
| Arquivo | Para quê |
|---|---|
| `claude/SKILL.md` | **Skill** (fluxo de 7 fases + regras) para Claude. `make skill` gera `dist/apple-motion-art.skill` com scripts, templates e referências |
| `claude/agents/apple-motion-art.md` | **Subagente** do Claude Code |
| `claude/agents/apple-motion-art.agent.md` | **Agente** do GitHub Copilot (VS Code) |

## O que muda com IA
O agente atua como um **editor de motion**:
1. **Pergunta** o que você quer (material PSD/plano, 3000×3000/4K, clima, o que mover e o que não mover, ideias livres, intensidade) — [15](15-diretor-criativo.md).
2. **Olha a capa** e cria o projeto (`init`), por PSD (camadas) ou capa plana (IA).
3. **Monta a animação** com `add-layer`, `add-effect`, `set`, `move`.
4. **Cria efeitos novos** (plugins em Python) quando o catálogo não cobre a sua ideia — [14](14-criar-efeitos.md).
5. **Mostra previews** (folha, frame, GIF), **pergunta o que ajustar** e itera.
6. **`check`** → render (um formato por vez) → **`validate_motion`** → entrega com limites honestos.

## Instalar
### Claude (claude.ai / Cowork)
```bash
make skill            # cria dist/apple-motion-art.skill
```
Importe o `.skill` em *Configurações → Skills*.
### Claude Code
```bash
mkdir -p ~/.claude/skills ~/.claude/agents
unzip dist/apple-motion-art.skill -d ~/.claude/skills/apple-motion-art
cp claude/agents/apple-motion-art.md ~/.claude/agents/
```
### GitHub Copilot (VS Code)
```bash
mkdir -p .github/agents
cp claude/agents/apple-motion-art.agent.md .github/agents/
```
Mantenha `scripts/`, `configs/` e `docs/` no repositório.

## Exemplos de pedido
> "Anime esta capa [3000×3000]. Quero algo sombrio, a pessoa respirando e o título pulsando em neon. UPC 7891234567890."

> "Aqui está o PSD. O logo não pode mexer. Faça a fumaça do fundo mais intensa e mostre um GIF antes de renderizar."

> "Crie um efeito de chuva de neon rosa na diagonal, bem sutil." (o agente escreve um plugin, testa com `check` e mostra o preview)

## Princípios
Ver [`claude/SKILL.md`](../claude/SKILL.md): pergunte antes de criar, mostre antes de renderizar, valide antes de dizer que terminou; efeitos nascem/morrem em zero; sem flashes; sem moldura; itens-chave na Safe Area; **nunca `pkill -f`**; honestidade sobre limites.

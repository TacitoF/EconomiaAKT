import disnake
from disnake.ext import commands
import asyncio
import database as db
from .constantes import get_limite, NUM_BARALHOS
from .sapato import Sapato
from .lobby import LobbyView
from .game import BlackjackView


class BlackjackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._sapatos: dict[int, Sapato] = {}

    def _get_sapato(self, channel_id: int) -> Sapato:
        if channel_id not in self._sapatos:
            self._sapatos[channel_id] = Sapato()
            total = self._sapatos[channel_id].total_inicial
            print(f"🃏 Novo sapato criado para o canal {channel_id} ({NUM_BARALHOS} baralhos, {total} cartas)")
        return self._sapatos[channel_id]

    async def cog_before_invoke(self, ctx):
        if ctx.channel.name != '🎰・akbet':
            canal  = disnake.utils.get(ctx.guild.channels, name='🎰・akbet')
            mencao = canal.mention if canal else "#🎰・akbet"
            await ctx.send(f"🐒 Ei {ctx.author.mention}, vá para o canal {mencao}.")
            raise commands.CommandError("Canal incorreto.")

    @commands.command(aliases=["bj", "21"])
    async def blackjack(self, ctx, aposta: float = None):
        if aposta is None:
            return await ctx.send(f"⚠️ {ctx.author.mention}, use: `!blackjack <valor>` ou `!21 <valor>`")
        if aposta <= 0:
            return await ctx.send("❌ Aposta inválida!")
        aposta = round(aposta, 2)

        try:
            u_c = db.get_user_data(str(ctx.author.id))
            if not u_c:
                return await ctx.send("❌ Conta não encontrada!")

            cargo = u_c['data'][3] if len(u_c['data']) > 3 else "Lêmure"
            saldo = db.parse_float(u_c['data'][2])
            if aposta > get_limite(cargo):
                return await ctx.send(f"🚫 Como **{cargo}**, seu limite é de **{get_limite(cargo)} MC**.")
            if saldo < aposta:
                return await ctx.send("❌ Saldo insuficiente!")

            sapato = self._get_sapato(ctx.channel.id)

            if sapato.precisa_embaralhar:
                aviso = await ctx.send("🔀 **O sapato está quase vazio — embaralhando novo sapato antes de começar...**")
                await asyncio.sleep(1.5)
                try: await aviso.delete()
                except: pass

            db.update_value(u_c['row'], 3, round(saldo - aposta, 2))

            # ── Lobby ──────────────────────────────────────────────────────
            lobby_view = LobbyView(ctx, self.bot, aposta, [ctx.author], sapato)
            msg = await ctx.send(lobby_view._lobby_text(), view=lobby_view)
            lobby_view.msg = msg
            await lobby_view.wait()

            # Devolve aposta do criador se cancelado
            if not lobby_view.started:
                p_db = db.get_user_data(str(ctx.author.id))
                if p_db:
                    db.update_value(p_db['row'], 3, round(db.parse_float(p_db['data'][2]) + aposta, 2))
                motivo = "por inatividade" if lobby_view.cancelled else ""
                return await ctx.send(f"⏰ Mesa cancelada {motivo}. Valores devolvidos.".strip())

            try:
                await lobby_view.msg.delete()
            except Exception:
                pass

            # ── Inicia o jogo ──────────────────────────────────────────────
            view = BlackjackView(
                ctx, self.bot, aposta,
                lobby_view.players, sapato,
                side_bets=lobby_view.side_bets
            )

            view.dealer_hand = [view._puxar_carta(), view._puxar_carta()]
            for p_id in view.player_ids:
                p = view.players_data[p_id]
                p["hand"] = [view._puxar_carta(), view._puxar_carta()]
                p["hand_ases_iniciais"] = sum(1 for c in p["hand"] if c["valor"] == "A")

            embed_loading = disnake.Embed(
                title="🃏 Distribuindo as cartas...", color=disnake.Color.dark_purple()
            )
            msg = await ctx.send(embed=embed_loading)
            view.message = msg

            msgs_side = view._resolver_side_bets_iniciais()
            if msgs_side:
                await ctx.send(
                    "🎰 **Resultados das Apostas Laterais:**\n" + "\n".join(msgs_side),
                    delete_after=15
                )

            # Blackjack Natural — marca quem tirou 21 de cara
            for p_id in view.player_ids:
                if view._get_pontos_mao(p_id, 1) == 21:
                    view.players_data[p_id]["status"] = "parou"

            await view.atualizar_embed()

            # Avança índice para o primeiro jogador que ainda está jogando
            while (
                view.current_player_idx < len(view.player_ids) and
                view.players_data[view.player_ids[view.current_player_idx]]["status"] == "parou"
            ):
                view.current_player_idx += 1

            if view.current_player_idx >= len(view.player_ids):
                await view._proximo_turno()

        except commands.CommandError:
            raise
        except Exception as e:
            print(f"❌ Erro no !blackjack de {ctx.author}: {e}")
            await ctx.send(f"⚠️ {ctx.author.mention}, ocorreu um erro. Tente novamente!")


def setup(bot):
    bot.add_cog(BlackjackCog(bot))
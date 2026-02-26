"""Main CLI entry point"""

import click
from pathlib import Path

from .commands.backtest import backtest
from .commands.trade import trade
from ..utils.config import get_config


@click.group()
@click.version_option(version='0.1.0')
@click.option('--log-level', default='INFO', help='日志级别')
@click.option('--config-dir', help='配置文件目录')
@click.pass_context
def cli(ctx, log_level, config_dir):
    """Bitcoin & Stock Trading System

    一个功能完整的实时量化交易系统
    """
    # Store log level in context for subcommands to use
    ctx.ensure_object(dict)
    ctx.obj['log_level'] = log_level
    ctx.obj['config_dir'] = config_dir

    # Don't setup logger here - let subcommands decide
    # This allows dashboard mode to suppress console output


# 注册命令组
cli.add_command(backtest)
cli.add_command(trade)


@cli.command()
def version():
    """显示版本信息"""
    click.echo("Bitcoin & Stock Trading System v0.1.0")
    click.echo("Powered by Claude Opus 4.6")


if __name__ == '__main__':
    cli()

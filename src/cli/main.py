"""Main CLI entry point"""

import click
from pathlib import Path

from .commands.backtest import backtest
from .commands.trade import trade
from ..utils.logger import setup_logger
from ..utils.config import get_config


@click.group()
@click.version_option(version='0.1.0')
@click.option('--log-level', default='INFO', help='日志级别')
@click.option('--config-dir', help='配置文件目录')
def cli(log_level, config_dir):
    """Bitcoin & Stock Trading System

    一个功能完整的实时量化交易系统
    """
    # 设置日志
    log_file = Path('./data/logs/trading.log')
    setup_logger(log_level=log_level, log_file=str(log_file))

    # 设置配置目录
    if config_dir:
        config = get_config()
        config.config_dir = Path(config_dir)


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

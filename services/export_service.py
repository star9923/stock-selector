"""
export_service.py - 数据导出服务
"""
import pandas as pd
import os
from datetime import datetime
from typing import List, Dict
import io


# 导出目录
EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)


def export_to_excel(data: List[Dict], filename: str, sheet_name: str = "数据") -> str:
    """
    导出数据到Excel
    :param data: 数据列表
    :param filename: 文件名（不含扩展名）
    :param sheet_name: 工作表名称
    :return: 文件路径
    """
    if not data:
        raise ValueError("没有数据可导出")

    df = pd.DataFrame(data)

    # 生成文件名（带时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(EXPORT_DIR, f"{filename}_{timestamp}.xlsx")

    # 导出到Excel
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)

        # 自动调整列宽
        worksheet = writer.sheets[sheet_name]
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width

    return filepath


def export_to_csv(data: List[Dict], filename: str) -> str:
    """
    导出数据到CSV
    :param data: 数据列表
    :param filename: 文件名（不含扩展名）
    :return: 文件路径
    """
    if not data:
        raise ValueError("没有数据可导出")

    df = pd.DataFrame(data)

    # 生成文件名（带时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(EXPORT_DIR, f"{filename}_{timestamp}.csv")

    # 导出到CSV（使用UTF-8 BOM以便Excel正确打开）
    df.to_csv(filepath, index=False, encoding='utf-8-sig')

    return filepath


def export_stock_selection(data: List[Dict], format: str = 'excel') -> str:
    """
    导出选股结果
    :param data: 选股数据
    :param format: 导出格式 ('excel' 或 'csv')
    :return: 文件路径
    """
    filename = "选股结果"

    if format == 'excel':
        return export_to_excel(data, filename, sheet_name="选股结果")
    else:
        return export_to_csv(data, filename)


def export_stock_analysis(analysis_data: Dict, format: str = 'excel') -> str:
    """
    导出股票分析报告
    :param analysis_data: 股票分析数据
    :param format: 导出格式
    :return: 文件路径
    """
    code = analysis_data.get('code', 'unknown')
    name = analysis_data.get('name', '')
    filename = f"股票分析_{name}_{code}"

    if format == 'excel':
        # 创建多个工作表
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(EXPORT_DIR, f"{filename}_{timestamp}.xlsx")

        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # 基本信息
            basic_info = analysis_data.get('basic_info', {})
            df_basic = pd.DataFrame([basic_info])
            df_basic.to_excel(writer, sheet_name="基本信息", index=False)

            # 技术分析
            technical = analysis_data.get('technical', {})
            df_tech = pd.DataFrame([technical])
            df_tech.to_excel(writer, sheet_name="技术分析", index=False)

            # 基本面分析
            fundamental = analysis_data.get('fundamental', {})
            df_fund = pd.DataFrame([fundamental])
            df_fund.to_excel(writer, sheet_name="基本面分析", index=False)

            # 情绪分析
            sentiment = analysis_data.get('sentiment', {})
            if sentiment:
                df_sentiment = pd.DataFrame([sentiment])
                df_sentiment.to_excel(writer, sheet_name="情绪分析", index=False)

            # 价格数据
            price_data = analysis_data.get('price_data', [])
            if price_data:
                df_price = pd.DataFrame(price_data)
                df_price.to_excel(writer, sheet_name="历史价格", index=False)

            # 交易信号
            signals = analysis_data.get('signals', [])
            if signals:
                df_signals = pd.DataFrame(signals)
                df_signals.to_excel(writer, sheet_name="交易信号", index=False)

        return filepath
    else:
        # CSV格式只导出基本信息
        export_data = {
            **analysis_data.get('basic_info', {}),
            **analysis_data.get('technical', {}),
            **analysis_data.get('fundamental', {}),
            **analysis_data.get('sentiment', {}),
        }
        return export_to_csv([export_data], filename)


def export_sector_analysis(sector_data: Dict, format: str = 'excel') -> str:
    """
    导出板块分析数据
    :param sector_data: 板块分析数据
    :param format: 导出格式
    :return: 文件路径
    """
    sector_name = sector_data.get('sector_name', 'unknown')
    filename = f"板块分析_{sector_name}"

    if format == 'excel':
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(EXPORT_DIR, f"{filename}_{timestamp}.xlsx")

        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # 板块概览
            summary = sector_data.get('summary', {})
            df_summary = pd.DataFrame([summary])
            df_summary.to_excel(writer, sheet_name="板块概览", index=False)

            # 板块情绪
            sentiment = sector_data.get('sector_sentiment', {})
            if sentiment:
                df_sentiment = pd.DataFrame([sentiment])
                df_sentiment.to_excel(writer, sheet_name="板块情绪", index=False)

            # 涨幅榜
            top_stocks = sector_data.get('top_stocks', {})
            if top_stocks:
                gainers = top_stocks.get('gainers', [])
                if gainers:
                    df_gainers = pd.DataFrame(gainers)
                    df_gainers.to_excel(writer, sheet_name="涨幅榜", index=False)

                losers = top_stocks.get('losers', [])
                if losers:
                    df_losers = pd.DataFrame(losers)
                    df_losers.to_excel(writer, sheet_name="跌幅榜", index=False)

        return filepath
    else:
        # CSV格式导出概览和涨幅榜
        summary = sector_data.get('summary', {})
        return export_to_csv([summary], filename)


def get_export_files() -> List[Dict]:
    """
    获取导出文件列表
    :return: 文件列表
    """
    files = []
    if os.path.exists(EXPORT_DIR):
        for filename in os.listdir(EXPORT_DIR):
            if filename.endswith(('.xlsx', '.csv')):
                filepath = os.path.join(EXPORT_DIR, filename)
                stat = os.stat(filepath)
                files.append({
                    'filename': filename,
                    'size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                })
    # 按创建时间倒序排列
    files.sort(key=lambda x: x['created_at'], reverse=True)
    return files


def delete_export_file(filename: str) -> bool:
    """
    删除导出文件
    :param filename: 文件名
    :return: 是否成功
    """
    filepath = os.path.join(EXPORT_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


def clean_old_exports(days: int = 7):
    """
    清理旧的导出文件
    :param days: 保留天数
    """
    if not os.path.exists(EXPORT_DIR):
        return

    now = datetime.now()
    for filename in os.listdir(EXPORT_DIR):
        filepath = os.path.join(EXPORT_DIR, filename)
        if os.path.isfile(filepath):
            file_time = datetime.fromtimestamp(os.path.getctime(filepath))
            if (now - file_time).days > days:
                os.remove(filepath)


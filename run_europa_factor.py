from factor_framework.europa import FACTORS
from test_factor_demo import strongFactorTest as FactorTest
from run_factor import run_factor
# import sys
# sys.path.append("../marketdata")


def run(factor_name,
        start_date=20160101,
        end_date=20181231,
        basic_file_path='/workspace/public/data/project/basic_data/20160101_20181231.pq',
        result_path='/workspace/factor_mining/example/factor_framework/europa/V20250930',
        n_jobs=16, cal_mi=False, factor_corr_test=True, generate_pdf=False):
    """运行单个因子计算与测试。

    Args:
        factor_name: 因子名称，如 'order_example'、'trade_example'、't1_example'
        start_date:   起始日期，默认 20160101
        end_date:     结束日期，默认 20181231
        basic_file_path: 基础样本数据路径
        result_path:  结果保存路径
        n_jobs:       并行线程数，默认使用因子模块中声明的 FACTOR_N_JOBS
        cal_mi:       是否计算互信息
        factor_corr_test: 是否做因子相关性测试
        generate_pdf: 是否生成 PDF 报告
    """
    factor_func, factor_type = FACTORS[factor_name]

    print(f"[因子: {factor_name}] [类型: {factor_type}] [并行数: {n_jobs}]")

    factor_df2, fill_dic = run_factor(
        factor_func, factor_name, factor_type,
        start_date, end_date, basic_file_path, result_path,
        interval_res=False, n_jobs=n_jobs,
    )

    factor_test = FactorTest(start_date, end_date, cal_mi=cal_mi)
    check_score_res, factor_corr = factor_test.factor_test(
        factor_df2,
        result_path=result_path,
        factor_corr_test=factor_corr_test,
        generate_pdf=generate_pdf,
    )
    return factor_df2, fill_dic, check_score_res, factor_corr


if __name__ == '__main__':
    factor_name = "xzt_20260622_1"
    result_path = './result'

    run(factor_name=factor_name, result_path=result_path)

import time
import re
import pandas as pd
from paddleocr import PaddleOCR
from pandas import merge_asof


class Analysis:

    def __init__(self,ocr_type, img_stream):

        pd.set_option('display.max_colwidth', None)
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)

        data = []
        ocr = PaddleOCR(
            use_angle_cls=True,  # 启用方向分类器
            lang='ch',  # 使用简体中文模型
            det_algorithm='DB',  # 文本检测算法选择DB   
            rec_algorithm='CRNN',  # 文本识别算法选择SVTR_LCNet
            use_space_char=True,
            layout=True,  # 启用布局分析
            table=True,  # 启用表格识别
            det_db_box_thresh=0.1,
            det_db_thresh=0.1,
        )
        result = ocr.ocr(img_stream, cls=True)
        print(result)
        for idx in range(len(result)):
            res = result[idx]
        for line in res:
            index = line[0]
            row = {"index_1": index[0][0], "index_2": index[0][1], "index_3": index[1][0], "index_4": index[1][1],
                   "index_5": index[2][0], "index_6": index[2][1], "index_7": index[3][0], "index_8": index[3][1],
                   "key": line[1][0].replace("：", ":").replace("_", "").replace("（", "(").replace("）", ")").replace(" ",
                                                                                                                    ""),
                   "accuracy": line[1][1]}
            data.append(row)
        data = pd.DataFrame(data)
        data = data.sort_values(by=['index_1', 'index_2'], ascending=[True, True])
        if ocr_type == 'vat_invoice':
              # 行高容错设置
            data["row_height"] = abs(data["index_4"] - data["index_6"]) / 2
            data["filed_height"] = data["index_6"] - data["index_4"]
            data["filed_length"] = data["index_3"] - data["index_7"]

            data["y_offset_up"] = data["index_2"] + data["filed_height"] * 3
            data["y_offset_low"] = data["index_2"] - data["filed_height"] * 3
            data["x_offset_up"] = data["index_3"] + data["filed_height"] * 3
            data["x_offset_low"] = data["index_7"] - data["filed_height"] * 3
            self.middle_y = (max(data["index_2"]) - min(data["index_2"])) / 2
            self.middle_x = (max(data["index_3"]) - min(data["index_3"])) / 2        
        elif ocr_type == 'ordinary_invoice':
            # 行高容错设置
            data["row_height"] = abs(data["index_4"] - data["index_6"]) / 2.5
            data["filed_height"] = data["index_6"] - data["index_4"]
            data["filed_length"] = data["index_3"] - data["index_7"]

            data["y_offset_up"] = data["index_2"] + data["filed_height"] * 0.5
            data["y_offset_low"] = data["index_2"] - data["filed_height"] * 0.5
            data["x_offset_up"] = data["index_3"] + data["filed_height"] * 0.5
            data["x_offset_low"] = data["index_7"] - data["filed_height"] * 0.5
            self.middle_y = (max(data["index_2"]) - min(data["index_2"])) / 2
            self.middle_x = (max(data["index_3"]) - min(data["index_3"])) / 2
        elif ocr_type == 'smart_invoice':
            # 行高容错设置
            data["row_height"] = abs(data["index_4"] - data["index_6"]) / 2.5
            data["filed_height"] = data["index_6"] - data["index_4"]
            data["filed_length"] = data["index_3"] - data["index_7"]

            data["y_offset_up"] = data["index_2"] + data["filed_height"] * 0.5
            data["y_offset_low"] = data["index_2"] - data["filed_height"] * 0.5
            data["x_offset_up"] = data["index_3"] + data["filed_height"] * 0.5
            data["x_offset_low"] = data["index_7"] - data["filed_height"] * 0.5
            self.middle_y = (max(data["index_2"]) - min(data["index_2"])) / 2
            self.middle_x = (max(data["index_3"]) - min(data["index_3"])) / 2
        else:
            # 行高容错设置
            data["row_height"] = abs(data["index_4"] - data["index_6"]) / 2.5
            data["filed_height"] = data["index_6"] - data["index_4"]
            data["filed_length"] = data["index_3"] - data["index_7"]

            data["y_offset_up"] = data["index_2"] + data["filed_height"] * 1
            data["y_offset_low"] = data["index_2"] - data["filed_height"] * 1
            data["x_offset_up"] = data["index_3"] + data["filed_height"] * 1
            data["x_offset_low"] = data["index_7"] - data["filed_height"] * 1
            self.middle_y = (max(data["index_2"]) - min(data["index_2"])) / 2
            self.middle_x = (max(data["index_3"]) - min(data["index_3"])) / 2

        print(data)
        self.data = data

    def data_handle(self, ocr_type: str):
        keys = self.data["key"].tolist()
        return getattr(self, ocr_type + "_analysis")()


    def merge_raw_data(self, fileds: dict):
        """
        合并原始数据
        :return:
        """

        def merge(filtered_df, join_flag=True):
            # filtered_df = filtered_df.sort_values(by=['index_2'], ascending=[True])
            if filtered_df.shape[0] >= 2:
                indexes_list = filtered_df.index.tolist()
                # 合并操作
                first_key = str(filtered_df["key"].iloc[0]).replace(":", "")
                remaining_keys = filtered_df["key"].iloc[1:]
                if join_flag:
                    new_key = first_key + ":" + "".join(remaining_keys.tolist())
                else:
                    new_key = "".join(filtered_df["key"].tolist())
                self.data.loc[indexes_list[0], 'key'] = new_key
                self.data.loc[indexes_list[0], 'index_3'] = filtered_df.loc[indexes_list[-1], 'index_3']
                self.data.loc[indexes_list[0], 'index_2'] = filtered_df.loc[indexes_list[-1], 'index_2']
                self.data.loc[indexes_list[0], 'index_7'] = filtered_df.loc[indexes_list[-1], 'index_7']

                self.data.drop(indexes_list[1:])

        for filed in fileds.keys():
            extension_multiplier_x = fileds.get(filed)
            if not extension_multiplier_x:
                if ":" in filed:
                    filed = filed.split(":")[0]
                start_text, end_text = filed[0], filed[-1]
                filtered_df = self.data[
                    (self.data['key'].str.startswith(start_text) | self.data['key'].str.endswith(end_text)) &
                    (self.data['y_offset_up'] >= self.data['index_2']) &
                    (self.data['index_2'] >= self.data['y_offset_low'])
                    ]
                merge(filtered_df, False)
            else:
                curr_df = self.data[self.data['key'].str.startswith(filed)]
                if curr_df.empty:
                    continue
                # x偏移设置
                shape = curr_df.shape[0]
                for i in range(shape):
                    curr_index_3 = curr_df.iloc[i]['index_3']
                    curr_filed_length = curr_df.iloc[i]['filed_length'] * extension_multiplier_x
                    curr_y_offset_up = curr_df.iloc[i]['y_offset_up']
                    y_offset_low = curr_df.iloc[i]['y_offset_low']

                    merge_x_offset = curr_index_3 + curr_filed_length
                    filtered_df = self.data[
                        (self.data['index_3'] >= curr_index_3) &
                        (merge_x_offset >= self.data['index_7']) &
                        (curr_y_offset_up >= self.data['index_2']) &
                        (self.data['index_2'] >= y_offset_low)
                        ]
                    merge(filtered_df)

    def vat_invoice_analysis(self):
            # 需要合并的字段
            fileds = {"收款人:": 0.3}

            self.merge_raw_data(fileds)
            名称 = self.analysis_index(key="名称:", direction="like")
            if 名称 and len(名称) > 0:
                购买方名称 = 名称[0].split(":")[1]
            else:
                购买方名称 = "未知购买方名称"  # 或记录日志

            if 名称 and len(名称) > 1:
                销售方名称 = 名称[1].split(":")[1]
            else:
                销售方名称 = "未知销售方名称"  # 或记录日志
            价税合计 = self.analysis_index(key=r'([壹贰叁肆伍陆柒捌玖拾佰仟零]+(?:零)?)*[圆园元](?:[零壹贰叁肆伍陆柒捌玖拾]+角)?(?:[零壹贰叁肆伍陆捌玖拾]+分)?(?:整)?', direction="like")
            价税合计大写 = "未知"
            if 价税合计 :
                价税合计大写=价税合计[0]
            价税合计小写 = self.analysis_index(key="(小写)", direction="like")
            开票日期 = self.analysis_index(key="开票日期:", direction="like")
            发票号码 = self.analysis_index(key="发票号码:", direction="like")
            开票人 = self.analysis_index(key="开票人:", direction="like")


            购买方纳税人识别号 = ""#self.analysis_index(key="纳税人识别号:", direction="like", block=1)[0].split(":")[1]
            销售方方纳税人识别号 = ""#self.analysis_index(key="纳税人识别号:", direction="like", block=3)[0].split(":")[1]
            税率 = self.analysis_index(key="税率", direction="below")
            购买方开户行及账号 = ""#self.analysis_index(key="开户行及账号", direction="like", block=3)
            销售方方开户行及账号 = ""#self.analysis_index(key="开户行及账号", direction="like", block=1)

            收款人 = self.analysis_index(key="收款人:", direction="like", block=1)

            print(self.data)
            data = {"开票日期": 开票日期, "发票号码": 发票号码, "购买方名称": 购买方名称, "销售方名称": 销售方名称,
                "价税合计大写": 价税合计大写,"价税合计小写": 价税合计小写, "开票人": 开票人}
            print(data)
            return data
    def train_invoice_analysis(self):

        姓名 = self.analysis_index(key=r'(\d{10}[\d\*]{8})([^\d]+)', direction="like")#
        时间 = self.analysis_index(key=r'\d{4}年\d{2}月\d{2}日\d{2}:\d{2}', direction="like")#
        出发地 = ""#
        价格 = self.analysis_index(key='￥', direction="like")#
        到达地 = ""#

        data = {"姓名": 姓名, "时间": 时间, "出发地": 出发地, "到达地": 到达地,"价格":价格}
        print(self.data)
        return data

    def ordinary_invoice_analysis(self):

        # 需要合并的字段
        fileds = {"数量": None, "合计": None}
        self.merge_raw_data(fileds)
        名称 = self.analysis_index(key="名称:", direction="like")
        if 名称 and len(名称) > 0:
            购买方名称 = 名称[0].split(":")[1]
        else:
            购买方名称 = "未知购买方名称"  # 或记录日志

        if 名称 and len(名称) > 1:
            销售方名称 = 名称[1].split(":")[1]
        else:
            销售方名称 = "未知销售方名称"  # 或记录日志
        价税合计 = self.analysis_index(key=r'([壹贰叁肆伍陆柒捌玖拾佰仟零]+(?:零)?)*[圆园元](?:[零壹贰叁肆伍陆柒捌玖拾]+角)?(?:[零壹贰叁肆伍陆捌玖拾]+分)?(?:整)?', direction="like")
        价税合计大写 = "未知"
        if 价税合计 :
            价税合计大写=价税合计[0]
        价税合计小写 = self.analysis_index(key="(小写)", direction="like")
        开票日期 = self.analysis_index(key="开票日期:", direction="like")
        发票号码 = self.analysis_index(key="发票号码:", direction="like")
        开票人 = self.analysis_index(key="开票人:", direction="like")

        项目名称 = self.analysis_index(key="项目名称", direction="below", below_height=8)
        规格型号 = self.analysis_index(key="规格型号", direction="below")
        单位 = self.analysis_index(key="单位", direction="below")
        数量 = self.analysis_index(key="数量", direction="below")
        金额 = self.analysis_index(key="金额", direction="below")
        税额 = self.analysis_index(key="税额", direction="below")
        金额合计 = self.analysis_index(key="金额", end_key="￥", direction="below")
        税额合计 = self.analysis_index(key="税额", end_key="￥", direction="below")
        if 金额合计:
            金额合计=金额合计[0]

        data = {"开票日期": 开票日期, "发票号码": 发票号码, "购买方名称": 购买方名称, "销售方名称": 销售方名称,
                "价税合计大写": 价税合计大写,"价税合计小写": 价税合计小写, "项目名称": 项目名称,
                "规格型号": 规格型号, "单位": 单位, "数量": 数量, "金额": 金额,"税额":税额,"金额合计":金额合计, "税额合计": 税额合计, "开票人": 开票人}
        print(data)
        return data

    def pay_invoice_analysis(self):
        银行卡号 = self.analysis_index(key=r"(\d{5,6}[\*]+)([\d]{4})", direction="like")
        金额 = self.analysis_index(key=r"(金额:)?RMB\:?\d+(\.\d+)?[\d)]$", direction="like")
        商户名称 = self.analysis_index(key="商户名称:", direction="like")
        时间 = self.analysis_index(key=r'(\d{4}[/\.-]\d{2}[/\.-]\d{2})\s*?(\d{2}:\d{2}:\d{2})', direction="like")
        银行名称=""
        if 银行卡号:
            银行名称=self.get_bank_name(银行卡号[0])
        data = {"银行名称":银行名称,"银行卡号":银行卡号,"金额":金额,"时间":时间,"商户名称":商户名称}
        print(data)
        return data

    def smart_invoice_analysis(self):
        时间 = self.analysis_index(key=r'^(2\d{3}-?\d{2}-?\d{2})$', direction="like")
        发票号码 = self.analysis_index(key='发票号码', direction="like")


        data={"发票号码":发票号码,"时间":时间}
        print(data)
        return data
    def plane_invoice_analysis(self):
        
        data={}
        print(data)
        return data
    def detail_invoice_analysis(self):
        时间 = self.analysis_index(key=r'(\d{4}[/\.-]\d{2}[/\.-]\d{2})\s*?(\d{2}:\d{2}:\d{2})', direction="like")
        商品说明 = self.analysis_index(key='商品说明', direction="like")
        付款方式 = self.analysis_index(key='付款方式', direction="like")
        收款方 = self.analysis_index(key='收款方', direction="like")
        金额 = self.analysis_index(key='<账单详情', direction="below",below_height=3)
        商户 = self.analysis_index(key="<账单详情", direction="below")

        data = {"商户":商户,"金额":金额,"收款方":收款方,"付款方式":付款方式,"时间":时间,"商品说明":商品说明}
        print(data)
        return data

    # 银行卡号BIN段示例（这里只列出了一些常见的银行）
    BANK_BIN_DICT = {
        "中国工商银行": ["6222", "6226", "6227", "6228", "6212", "6216"],
        "中国建设银行": ["6227", "6228", "6258"],
        "中国农业银行": ["6225", "6223", "6251"],
        "中国银行": ["6232", "6213", "6222", "6217"],
        "交通银行": ["6222", "6215", "6225"],
        "招商银行": ["6225", "6219", "6212", "6210"],
        "兴业银行": ["6229", "6230"],
        "中信银行": ["6223", "6225", "6210"],
        "浦发银行": ["6213", "6221"],
        "广发银行": ["6212", "6227"],
        "VISA": ["4"],  # VISA卡的BIN是以4开头
        "MasterCard": ["5"],  # MasterCard卡的BIN是以5开头
        "美国运通": ["34", "37"],  # AMEX卡的BIN是以34或37开头
        "发现卡": ["6011"]  # Discover卡的BIN是以6011开头
    }
    def get_bank_name(self,card_number):
        # 获取银行卡号的前六位作为BIN号段
        cleaned_card_number = re.sub(r'\D', '', card_number)
        bin_prefix = cleaned_card_number[:6]
        
        # 查找卡号对应的银行
        for bank_name, bin_list in self.BANK_BIN_DICT.items():
            for bin in bin_list:
                if bin_prefix.startswith(bin):
                    return bank_name

        return "无法识别该银行卡"
    
    def clean_data(self,key,data_list):
        # 使用列表推导式移除与 `key` 相等的项
        return [item for item in data_list if item != key]

    def analysis_index(self, key, direction, end_key=None, block=-1, below_height=2):

        """
        解析key 方向的匹配
        :param key:
        :param direction: below / right like
        :return:
        """

        append_block_filter = ""
        if block == 1:
            append_block_filter = f"and  index_2 >= {self.middle_y} and index_7 <= {self.middle_x}"
        if block == 2:
            append_block_filter = f"and index_2 >= {self.middle_y} and index_7 >= {self.middle_x}"
        if block == 3:
            append_block_filter = f"and index_2 <= {self.middle_y} and  index_7 <= {self.middle_x}"
        if block == 4:
            append_block_filter = f"and index_2 <= {self.middle_y} and index_7 >= {self.middle_x}"

        start_in_words = self.data.query(f'key=="{key}"')
        if direction == "like":
            expr = 'key.str.contains(@key, case=False, na=False)'
            expr += append_block_filter
            curr_key = self.data.query(expr, engine='python')
            return self.clean_data(key,curr_key["key"].tolist())
        if end_key is not None:
            end_key = end_key.strip()
            end_in_words = self.data[self.data['key'].str.startswith(end_key, na=False)]
            if end_in_words.empty:
                print(f"Error: No data found for key: {key} and end_key: {end_key}")
                return None  # 或者你可以返回一个默认值
            end_row = end_in_words.iloc[0]
        if not start_in_words.empty:
            first_row = start_in_words.iloc[0]
            if end_key is not None and direction == "right":
                # query_str = f'{first_row["y_offset_low"]} <= index_2 <= {first_row["y_offset_up"]} and index_1 != {first_row["index_1"]} and index_7 <= {end_row["index_7"]}'
                query_str = f'{first_row["y_offset_low"]} <= index_2 <= {first_row["y_offset_up"]} and index_1 != {first_row["index_1"]} and index_7 <= {end_row["index_3"]}'
                query_str += append_block_filter
                filter_values_words_value = self.data.query(query_str)

            elif end_key is None and direction == "right":
                query_str = f'{first_row["y_offset_low"]} < index_2 < {first_row["y_offset_up"]} and index_1 != {first_row["index_1"]} and {first_row["index_3"]}<= index_7 <= {first_row["index_3"] + first_row["filed_length"]}'
                query_str += append_block_filter
                filter_values_words_value = self.data.query(query_str)

            elif end_key is None and direction == "below":
                # 左对齐 或右对齐
                filed_height = first_row["filed_height"] * below_height
                query_str = f' {first_row["x_offset_low"]} <= index_3 and {first_row["x_offset_up"]} >= index_7 and  {first_row["index_2"]}+{filed_height} >= index_2  and {first_row["index_2"]}<= index_2'
                # query_str = f' ({first_row["x_offset_low"]} < index_3 < {first_row["x_offset_up"]} and {first_row["index_2"]} <= index_2 <= {first_row["index_2"]}+ {filed_height * 2} and index_2 != {first_row["index_2"]}) or ({first_row["x_offset_low"]} < index_7 < {first_row["x_offset_up"]} and {first_row["index_2"]} <= index_2 <= {first_row["index_2"]}+ {filed_height * 2} and index_2 != {first_row["index_2"]})'
                query_str += append_block_filter
                filter_values_words_value = self.data.query(query_str)

            elif end_key is not None and direction == "below":
                # 左对齐 或右对齐
                query_str = f' {first_row["x_offset_low"]} < index_3 and {first_row["x_offset_up"]} > index_7 and  {end_row["index_2"]} > y_offset_low  and {end_row["index_2"]} < y_offset_up'
                query_str += append_block_filter
                filter_values_words_value = self.data.query(query_str)
            return self.clean_data(key,filter_values_words_value["key"].tolist())
        else:
            return []


if __name__ == '__main__':
    ao = Analysis("../imgs/电子发票/IMG_20241231_141457.jpg")
    #ao.data_handle("ordinary_invoice")
    ao.analysis_index(key="价税合计(大写)", direction="right", end_key="小写")
    # ao.analysis_index(key="项目名称", direction="below")
    # ao.analysis_index(key="规格型号", direction="below")
    # ao.analysis_index(key="单位", direction="below")
    # ao.analysis_index(key="数量", direction="below")
    # ao.analysis_index(key="金额", direction="below")
    # ao.analysis_index(key="税额", direction="below")
    # ao.analysis_index(key="名称:", direction="like", block=1)
    # ao.analysis_index(key="名称:", direction="like", block=2)
    # index_1  index_2  index_3  index_4  index_5  index_6  index_7  index_8  \
# 26    472.0    143.0    499.0    143.0    499.0    154.0    472.0    154.0    税率
# 33    483.0    156.0    500.0    156.0    500.0    169.0    483.0    169.0    3%
# 60    147.0   1105.0   1054.0   1110.0   1054.0   1146.0    147.0   1142.0


# query_str = f' ({first_row["x_offset_low"]} < index_3 < {first_row["x_offset_up"]}
# and {first_row["index_2"]} <= index_2 <= {first_row["index_2"]}+ {filed_height}
# and index_2 != {first_row["index_2"]}) or
# ({first_row["x_offset_low"]} < index_7 < {first_row["x_offset_up"]}
# and {first_row["index_2"]} <= index_2 <= {first_row["index_2"]}+ {filed_height}
# and index_2 != {first_row["index_2"]})'

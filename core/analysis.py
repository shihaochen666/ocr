import pandas as pd
from paddleocr import PaddleOCR


class Analysis:

    def __init__(self, img_stream):

        pd.set_option('display.max_colwidth', None)
        pd.set_option('display.max_rows', None)
        pd.set_option('display.max_columns', None)

        data = []
        ocr = PaddleOCR(
            use_angle_cls=True,  # 启用方向分类器
            lang='ch',  # 使用简体中文模型
            det_algorithm='DB',  # 文本检测算法选择DB
            rec_algorithm='SVTR_LCNet',  # 文本识别算法选择SVTR_LCNet
            use_space_char=True,
            layout=True,  # 启用布局分析
            table=True,  # 启用表格识别
            det_db_box_thresh=0.6,
            det_db_thresh=0.4,
        )
        result = ocr.ocr(img_stream,cls=True)
        for idx in range(len(result)):
            res = result[idx]
        for line in res:
            index = line[0]
            row = {"index_1": index[0][0], "index_2": index[0][1], "index_3": index[1][0], "index_4": index[1][1],
                   "index_5": index[2][0], "index_6": index[2][1], "index_7": index[3][0], "index_8": index[3][1],
                   "key": line[1][0].replace("：", ":").replace("_", "").replace("（", "(").replace("）", ")"), "accuracy": line[1][1]}
            data.append(row)
        data = pd.DataFrame(data)
        data = data.sort_values(by=['index_1', 'index_2'], ascending=[True, True])
        # 行高容错设置
        data["row_height"] = abs(data["index_4"] - data["index_6"]) / 2.5
        data["y_offset_up"] = data["index_2"] + data["row_height"]
        data["y_offset_low"] = data["index_2"] - data["row_height"]
        data["x_offset_up"] = data["index_3"] * 1.01
        data["x_offset_low"] = data["index_7"] * 0.99
        data["filed_length"] = data["index_3"] - data["index_7"]
        data["filed_height"] = data["index_6"] - data["index_4"]
        self.middle_y = (max(data["index_2"]) - min(data["index_2"])) / 2
        self.middle_x = (max(data["index_3"]) - min(data["index_3"])) / 2
        print(data)
        self.data = data

    def data_handle(self,ocr_type:str):
        keys = self.data["key"].tolist()
        return getattr(self, ocr_type + "_analysis")()

    def merge_raw_data(self, fileds: dict):
        """
        合并原始数据
        :return:
        """

        def merge(filtered_df):
            filtered_df = filtered_df.sort_values(by=['index_2'], ascending=[True])
            if filtered_df.shape[0] >= 2:
                indexes_list = filtered_df.index.tolist()
                # 合并操作
                first_key = filtered_df["key"].iloc[0].split(":", "")
                remaining_keys = filtered_df["key"].iloc[1:]
                new_key = first_key + ":" + " ".join(remaining_keys.tolist())
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
                merge(filtered_df)
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

    def ordinary_invoice_analysis(self):
        # 需要合并的字段
        fileds = ["数量", "合计"]
        self.merge_raw_data(fileds)

        购买方名称 = self.analysis_index(key="名称:", direction="like", block=1)
        if 购买方名称:
            购买方名称 = 购买方名称[0].split(":")[1]
        销售方名称 = self.analysis_index(key="名称:", direction="like", block=2)
        if 销售方名称:
            销售方名称 = 销售方名称[0].split(":")[1]
        价税合计 = self.analysis_index(key="价税合计(大写)", direction="right", end_key="小写")
        项目名称 = self.analysis_index(key="项目名称", direction="below")
        规格型号 = self.analysis_index(key="规格型号", direction="below")
        单位 = self.analysis_index(key="单位", direction="below")
        数量 = self.analysis_index(key="数量", direction="below")
        金额 = self.analysis_index(key="金额", direction="below")
        税额 = self.analysis_index(key="税额", direction="below")
        开票日期=self.analysis_index(key="开票日期:", direction="like")
        发票号码=self.analysis_index(key="发票号码:", direction="like")
        开票人=self.analysis_index(key="开票人:", direction="like")

        data = {"开票日期":开票日期,"发票号码":发票号码,"购买方名称": 购买方名称, "销售方名称": 销售方名称,"价税合计": 价税合计, "项目名称": 项目名称,
             "规格型号": 规格型号, "单位": 单位, "数量": 数量,"金额": 金额, "税额": 税额,"开票人":开票人 }
        print(data)
        return data


    def vat_invoice_analysis(self):
        # 需要合并的字段
        fileds = ["数量", "合计"]
        self.merge_raw_data(fileds)
        价税合计 = self.analysis_index(key="价税合计(大写)", direction="right", end_key="小写")
        项目名称 = self.analysis_index(key="项目名称", direction="below")
        规格型号 = self.analysis_index(key="规格型号", direction="below")
        单位 = self.analysis_index(key="单位", direction="below")
        数量 = self.analysis_index(key="数量", direction="below")
        金额 = self.analysis_index(key="金额", direction="below")
        税额 = self.analysis_index(key="税额", direction="below")
        购买方名称 = self.analysis_index(key="名称:", direction="like", block=1)
        if 购买方名称:
            购买方名称 = 购买方名称[0].split(":")[1]
        销售方名称 = self.analysis_index(key="名称:", direction="like", block=2)
        if 销售方名称:
            销售方名称 = 销售方名称[0].split(":")[1]

        data = {"价税合计": 价税合计, "项目名称": 项目名称, "规格型号": 规格型号, "单位": 单位, "数量": 数量,
                "金额": 金额, "税额": 税额, "购买方名称": 购买方名称, "销售方名称": 销售方名称}
        print(data)
        return data

    def analysis_index(self, key, direction, end_key=None, block=-1):

        """
        解析key 方向的匹配
        :param key:
        :param direction: below / right like
        :return:
        """
        append_block_filter = ""
        if block == 1:
            append_block_filter = f"and  index_2 >= {self.middle_y} and index_3 <= {self.middle_x}"
        if block == 2:
            append_block_filter = f"and index_2 >= {self.middle_y} and index_3 >= {self.middle_x}"
        if block == 3:
            append_block_filter = f"and index_2 <= {self.middle_y} and  index_3 <= {self.middle_x}"
        if block == 4:
            append_block_filter = f"and index_2 <= {self.middle_y} and index_3 >= {self.middle_x}"

        start_in_words = self.data.query(f'key=="{key}"')
        if direction == "like":
            expr = 'key.str.contains(@key, case=False, na=False)'
            expr += append_block_filter
            curr_key = self.data.query(expr, engine='python')
            # print(curr_key["key"].tolist())
            return curr_key["key"].tolist()
        if end_key is not None:
            end_in_words = self.data.query('key.str.contains(@end_key, case=False, na=False)', engine='python')
            end_row = end_in_words.iloc[0]
        if not start_in_words.empty:
            first_row = start_in_words.iloc[0]
            if end_key is not None and direction == "right":
                query_str = f'{first_row["y_offset_low"]} < index_2 < {first_row["y_offset_up"]} and index_1 != {first_row["index_1"]} and index_8 <= {end_row["index_8"]}'
                query_str += append_block_filter
                filter_values_words_value = self.data.query(query_str)

            elif end_key is None and direction == "right":
                query_str = f'{first_row["y_offset_low"]} < index_2 < {first_row["y_offset_up"]} and index_1 != {first_row["index_1"]} and {first_row["index_3"]}<= index_8 <= {first_row["index_3"] + first_row["filed_length"]}'
                query_str += append_block_filter
                filter_values_words_value = self.data.query(query_str)

            elif end_key is None and direction == "below":
                # 左对齐 或右对齐
                filed_height = first_row["filed_height"]
                query_str = f' ({first_row["x_offset_low"]} < index_3 < {first_row["x_offset_up"]} and {first_row["index_2"]} <= index_2 <= {first_row["index_2"]}+ {filed_height} and index_2 != {first_row["index_2"]}) or ({first_row["x_offset_low"]} < index_7 < {first_row["x_offset_up"]} and {first_row["index_2"]} <= index_2 <= {first_row["index_2"]}+ {filed_height} and index_2 != {first_row["index_2"]})'
                query_str += append_block_filter
                filter_values_words_value = self.data.query(query_str)

            elif end_key is not None and direction == "below":
                # 左对齐 或右对齐
                filed_height = end_row["filed_height"]
                query_str = f' ({first_row["x_offset_low"]} < index_3 < {first_row["x_offset_up"]} and {first_row["index_2"]} <= index_2 <= {first_row["index_2"]}+ {filed_height} and index_2 != {first_row["index_2"]}) or ({first_row["x_offset_low"]} < index_7 < {first_row["x_offset_up"]} and {first_row["index_2"]} <= index_2 <= {first_row["index_2"]}+ {filed_height} and index_2 != {first_row["index_2"]})'
                query_str += append_block_filter
                filter_values_words_value = self.data.query(query_str)
            return filter_values_words_value["key"].tolist()
        else:
            return []


if __name__ == '__main__':
    ao = Analysis("../imgs/1.jpg")
    ao.data_handle()
    # ao.analysis_index(key="价税合计(大写)", direction="right", end_key="小写")
    # ao.analysis_index(key="项目名称", direction="below")
    # ao.analysis_index(key="规格型号", direction="below")
    # ao.analysis_index(key="单位", direction="below")
    # ao.analysis_index(key="数量", direction="below")
    # ao.analysis_index(key="金额", direction="below")
    # ao.analysis_index(key="税额", direction="below")
    # ao.analysis_index(key="名称:", direction="like", block=1)
    # ao.analysis_index(key="名称:", direction="like", block=2)

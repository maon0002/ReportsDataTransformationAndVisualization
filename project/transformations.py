import re
from datetime import datetime
from typing import List, Dict
import pandas as pd
from project._collections import Collection
from project.dataframes import BaseDataframe


class Transformation:

    @staticmethod
    def annual_to_monthly_report_df(report_dataframe: pd.DataFrame, datetime_format: str) -> pd.DataFrame:
        correct_input = False
        chosen_month = None
        while True:

            if correct_input:
                break
            chosen_month = input(f"Please chose the Year and the Month (YYYY-MM)\n"
                                 f"for the monthly reports in a correct format\n"
                                 f"*'2023-03' for example is March 2023:   ")

            correct_input = re.search(r'(\d{4}-\d{2})', chosen_month.strip())


        chosen_month_obj = datetime.strptime(chosen_month.strip() + "-01 00:00:00", datetime_format)

        chosen_month = pd.Series(chosen_month_obj).dt.to_period('M')
        monthly_data_df = report_dataframe.loc[report_dataframe['start_time'].dt.to_period('M').isin(chosen_month)]. \
            reset_index(drop=True)
        return monthly_data_df

    @staticmethod
    def sorted_dataframe(dataframe: pd.DataFrame, column: str):
        dataframe.sort_values(by=column, ascending=False, inplace=True)
        return dataframe

    @staticmethod
    def main(dataframe: pd.DataFrame, limitations_dataframe: pd.DataFrame) -> dict:
        """
        Transform the monthly and the annual df columns
        """
        flags_data_df = pd.DataFrame(Collection.flags_dict())
        limitations_df = BaseDataframe.limitations_func(limitations_dataframe)
        df = BaseDataframe.rename_original_report_columns(dataframe)

        # add column for issues
        df['flags'] = ""
        df['emp_names_input'] = '|' + df['f_name'] + '|' + df['l_name'] + '|'

        # rough cleaning of the columns data
        df = BaseDataframe.unwanted_chars(df)
        df = BaseDataframe.trim_all_columns(df)

        # transliteration of cyrillic to latin chars
        df["first_name"] = Collection.transliterate_bg_to_en(df, "f_name", "first_name")
        df["last_name"] = Collection.transliterate_bg_to_en(df, "l_name", "last_name")

        # using first, last name and email parts
        df = BaseDataframe.nickname(df)

        # get only the company name and if the training was IN PERSON/LIVE or ONLINE
        df = BaseDataframe.company_subtraction(df)

        # merge/vlookup the columns from limitations_df to the monthly/annual df
        df = pd.merge(
            left=df,
            right=limitations_df,
            left_on='company',
            right_on='company',
            how='left')

        # add columns for counting unique emp|company values w/ totals
        df = BaseDataframe.training_per_emp(df)

        # check phone values
        df = BaseDataframe.phone_validation(df)

        # substring trainers from calendar via regex.
        df = BaseDataframe.trainer(df)

        # check if the training date is between the dates when company contract starts and ends
        df = BaseDataframe.active_contracts(df)

        # create a Month name column
        df["month"] = [pd.Timestamp(x).month_name() for x in df["start_time"]]

        # create a Year name column
        df["year"] = [pd.Timestamp(x).year for x in df["start_time"]]

        # add column with the name of the day when training was take place
        df['dayname'] = df['start_time'].dt.day_name()

        # reformat start_time
        df['training_datetime'] = BaseDataframe.datetime_normalize(df['start_time'])

        # change from datetime to date only
        df['scheduled_date'] = BaseDataframe.date_normalize(df['scheduled_on'])
        df['training_end'] = BaseDataframe.date_normalize(df['end_time'])

        # define/make the raw reports and extract them to .csv
        full_raw_report_df = df
        full_raw_report_df.attrs['name'] = "raw_full"
        monthly_raw_report_df = Transformation.annual_to_monthly_report_df(full_raw_report_df,
                                                                           Collection.datetime_final_format())
        monthly_raw_report_df.attrs['name'] = "raw_mont"

        # separate and select only needed columns for new pd sets
        columns_list = Collection.new_data_columns()

        new_full_data_df = full_raw_report_df[columns_list]
        new_full_data_df.attrs['name'] = "new_full"
        new_monthly_data_df = monthly_raw_report_df[columns_list]
        new_monthly_data_df.attrs['name'] = "new_mont"

        total_trainings_df = BaseDataframe.total_trainings_func(new_monthly_data_df, new_full_data_df)[0]
        total_trainings_df.attrs['name'] = "total_trainings"
        report_trainers_df = BaseDataframe.total_trainings_func(new_monthly_data_df, new_full_data_df)[1]
        report_trainers_df.attrs['name'] = "report_trainers"

        # [print(x) for x in locals() if x.endswith("_df")]
        dfs_dict = {
            "total_trainings_df": total_trainings_df,
            "report_trainers_df": report_trainers_df,
            "new_monthly_data_df": new_monthly_data_df,
            "new_full_data_df": new_full_data_df,
            "limitations_df": limitations_df,
            "flags_data_df": flags_data_df,
            "full_raw_report_df": full_raw_report_df,
            "monthly_raw_report_df": monthly_raw_report_df,
        }

        return dfs_dict
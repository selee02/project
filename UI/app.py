from flask import Flask, render_template, render_template_string, request, redirect, url_for, session
from src.pipeline import track_a_pipeline, track_b_pipeline
import pandas as pd
import yfinance as yf
import os


# Flask class 생성 -> 초기화 과정 
# 웹서버를 생성
# __name__ : 현재 파일의 이름
app = Flask(__name__)
app.secret_key = 'your_secret_key_here' # 실제 배포 시에는 강력한 키로 변경해야 합니다.

# Login Logic
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # 간단한 테스트용 계정 (admin / 1234)
        if username == 'Judy' and password == '1234':
            # 로그인 성공 시 
            session['user'] = username
            return redirect(url_for('index'))
        else:
            # 로그인 실패 시
            from flask import flash
            flash('Invalid Username or Password')
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

# 2016년부터 2024년까지 kospi200에 한번만이라도 들어온 종목들의 점수와 랭크, 영향력이 있는 펙터들을 생성하여 rank_model에 저장
# short데이터와 long 데이터를 dict 형태로 저장
    # {"ranking_short_daily": DataFrame,
    # "ranking_long_daily": DataFrame,
    # "ui_payload": dict,
    # "artifacts_path": dict,
    # }
### rank_model = track_a_pipeline.run_track_a_pipeline()

# rank_model에서 short데이터와 long데이터를 가져옴
### short = rank_model['ranking_short_daily']
### long = rank_model['ranking_long_daily']


# 함수 생성 
# 시장 지표 가져오기
def get_market_indices():
    # 코스피, 코스닥, 나스닥, 환율의 티커 지정
    tickers = {
        'kospi': '^KS11',
        'kosdaq': '^KQ11', 
        'nasdaq': '^IXIC',
        'exchange': 'KRW=X'
    }
    # 빈 dict 생성
    indices = {}
    # 티커별 데이터 가져오기
    # 티커별 데이터 가져오기
    for name, ticker in tickers.items():
        try:
            data = yf.Ticker(ticker)
            # 5일치 데이터를 가져와서 전일 대비 변화량 계산
            hist = data.history(period="5d")
            
            if len(hist) >= 2:
                current_price = hist['Close'].iloc[-1]
                prev_price = hist['Close'].iloc[-2]
                
                change = current_price - prev_price
                pct_change = (change / prev_price) * 100
                
                # 부호와 색상, 아이콘 결정
                if change > 0:
                    sign = "up"
                    color = "text-danger" # 한국은 상승이 빨간색
                    icon = "mdi-arrow-up"
                elif change < 0:
                    sign = "down"
                    color = "text-primary" # 한국은 하락이 파란색
                    icon = "mdi-arrow-down"
                else:
                    sign = "steady"
                    color = "text-muted"
                    icon = "mdi-minus"

                indices[name] = {
                    'price': f"{current_price:,.2f}",
                    'change': f"{change:,.2f}",
                    'pct_change': f"{pct_change:,.2f}%",
                    'sign': sign,
                    'color': color,
                    'icon': icon
                }
            elif not hist.empty:
                 indices[name] = {
                    'price': f"{hist['Close'].iloc[-1]:,.2f}",
                    'change': "0.00",
                    'pct_change': "0.00%",
                    'sign': "steady",
                    'color': "text-muted",
                    'icon': "mdi-minus"
                 }
            else:
                 indices[name] = {
                    'price': "N/A", 
                    'change': "-", 
                    'pct_change': "-", 
                    'color': "", 
                    'icon': ""
                 }
        except Exception as e:
            print(f"Error fetching {name}: {e}")
            indices[name] = {
                'price': "Error", 
                'change': "-", 
                'pct_change': "-", 
                'color': "", 
                'icon': ""
            }
    # dict 데이터를 반환(되돌려준다) -> 함수를 호출했을때 해당 데이터를 되돌려준다. 
    # {'kospi': 3000, 'kosdaq': 1000, 'nasdaq': 1000, 'exchange': 1000}
    return indices

def format_name(s):
    return s.replace("(", " (")

# track_a_pipeline에서 생성된 short데이터와 long데이터를 사용하여 rank_data_set 함수를 생성
# 매개변수 _date를 사용하여 해당 날짜의 short데이터와 long데이터를 가져옴
def rank_data_set(_date):
    # _date를 이용하여 데이터를 인덱스 필터링 (loc 이용)
    # sort_values(by='rank_total')를 이용하여 rank_total을 기준으로 정렬 ( 정렬의 순서의 기본값 오름차순 )
    short = pd.read_csv('holdout_daily_ranking_short_top20.csv')
    long = pd.read_csv('holdout_daily_ranking_long_top20.csv')
    integrated = pd.read_csv('holdout_daily_ranking_integrated_top20.csv')
    
    short['종목명(ticker)'] = short['종목명(ticker)'].map(format_name)
    long['종목명(ticker)'] = long['종목명(ticker)'].map(format_name)
    integrated['종목명(ticker)'] = integrated['종목명(ticker)'].map(format_name)
    short_rank = short[short['날짜'] <= _date].tail(20).sort_values(by='랭킹')
    long_rank = long[long['날짜'] <= _date].tail(20).sort_values(by='랭킹')
    integrated_rank = integrated[integrated['날짜'] <= _date].tail(20).sort_values(by='랭킹')
    short['top3 피쳐그룹'] = short['top3 피쳐그룹'].astype(str).str.split(',')
    long['top3 피쳐그룹'] = long['top3 피쳐그룹'].astype(str).str.split(',')
    integrated['top3 피쳐그룹'] = integrated['top3 피쳐그룹'].astype(str).str.split(',')
    df_short = pd.DataFrame(list(short['top3 피쳐그룹'].values))
    df_long = pd.DataFrame(list(long['top3 피쳐그룹'].values))
    df_integrated = pd.DataFrame(list(integrated['top3 피쳐그룹'].values))
    df_short.rename(columns={0: 'top1', 1: 'top2', 2: 'top3'}, inplace=True)
    df_long.rename(columns={0: 'top1', 1: 'top2', 2: 'top3'}, inplace=True)
    df_integrated.rename(columns={0: 'top1', 1: 'top2', 2: 'top3'}, inplace=True)
    # ticker 별로 score_total을 합산
    # total_rank = short_rank.set_index('ticker')[['score_short']] + long_rank.set_index('ticker')[['score_long']]
    # ticker를 열로 변환하고 인덱스를 초기화
    # total_rank = total_rank.reset_index()
    # sort_values()를 이용해서 score_total을 기준으로 정렬 ( 내림차순 )
    # total_rank = total_rank.sort_values(by='score_total', ascending=False)
    # rank_total을 score_total을 기준으로 순위를 매김 ( 내림차순 )
    # total_rank['rank_total'] = total_rank['score_total'].rank(ascending=False)
    # 상위 15개 데이터만 가져오기

    # total_rank = total_rank.head(15)
    # score_total을 소수점 2자리로 반올림
    short_rank['score_total'] = short_rank['score'].round(2)
    short_rank['rank_total'] = short_rank['랭킹'].astype(int)
    long_rank['score_total'] = long_rank['score'].round(2)
    long_rank['rank_total'] = long_rank['랭킹'].astype(int)
    integrated_rank['score_total'] = integrated_rank['score'].round(2)
    integrated_rank['rank_total'] = integrated_rank['랭킹'].astype(int)
    short_rank['top1'] = df_short['top1']
    short_rank['top2'] = df_short['top2']
    short_rank['top3'] = df_short['top3']
    long_rank['top1'] = df_long['top1']
    long_rank['top2'] = df_long['top2']
    long_rank['top3'] = df_long['top3']
    integrated_rank['top1'] = df_integrated['top1']
    integrated_rank['top2'] = df_integrated['top2']
    integrated_rank['top3'] = df_integrated['top3']
    # total_rank['score_total'] = total_rank['score_total'].round(2)
    # total_rank['rank_total'] = total_rank['rank_total'].astype(int)
    short_dict = short_rank.to_dict(orient='records')
    long_dict = long_rank.to_dict(orient='records')
    integrated_dict = integrated_rank.to_dict(orient='records')
    # total_dict = total_rank.to_dict(orient='records')
    return short_dict, long_dict, integrated_dict


@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    # 유저가 특정 시간을 보냈는가? -> check
    # request -> 유저가 요청을 보냈을때
    # args -> get 방식으로 보낸 요청에서 데이터가 저장되어있는 공간 (식당에서 음식을 주문하고 옵션을 선택했을때 )
    # 유저가 보낸 데이터의 형태는 dict형태 -> get() dict에서 특정 키의 value를 출력
    input_date = request.args.get('date')
    # 유저가 시간을 보내지 않은 경우 -> 페이지에 처음 접속했을때
    if not input_date:
        # 실제 -> 오늘의 날짜 (Test로 2024-12-30 고정)
        input_date = "2024-12-30"
    
    # rank_data_set 함수를 호출하여 short_dict, long_dict, total_dict를 저장
    # UI에서 보여주기 위함
    short_dict, long_dict, integrated_dict = rank_data_set(input_date)
    short_dict, long_dict, integrated_dict = rank_data_set(input_date)
    
    # 그래프를 그리기 위한 데이터 (CSV 파일 읽기)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # NEW CSV FILE: dummy_kospi200_pr_tabs_4lines_2023_2024_v5.csv
    csv_path = os.path.join(base_dir, 'dummy_kospi200_pr_tabs_4lines_2023_2024_v5.csv')
    
    all_chart_data = {}
    holding_periods = [20, 40, 60, 80, 100, 120] # List of integers to match horizon_days

    # CSV 파일이 존재하는지 확인하고 읽기
    try:
        df_chart = pd.read_csv(csv_path)
        
        # 각 Holding Period 별로 데이터셋 구성
        for period in holding_periods:
            # Filter by horizon_days
            period_df = df_chart[df_chart['horizon_days'] == period]
            
            if period_df.empty:
                all_chart_data[str(period)] = {'labels': [], 'datasets': []}
                continue

            # month 컬럼을 리스트로 변환 (Labels)
            common_labels = period_df['month'].tolist()
            
            datasets = []
            
            # 1. KOSPI (kospi200_pr_cum_return_pct)
            if 'kospi200_pr_cum_return_pct' in period_df.columns:
                datasets.append({
                    'label': 'KOSPI',
                    'data': period_df['kospi200_pr_cum_return_pct'].tolist(),
                    'borderColor': '#587ce4'
                })

            # 2. Short (short_cum_return_pct)
            if 'short_cum_return_pct' in period_df.columns:
                datasets.append({
                    'label': '단기 (BT20)', # Label kept as BT20 for consistency, or just '단기'
                    'data': period_df['short_cum_return_pct'].tolist(),
                    'borderColor': '#ede190'
                })
            
            # 3. Long (long_cum_return_pct)
            if 'long_cum_return_pct' in period_df.columns:
                datasets.append({
                    'label': '장기 (BT120)', # Label kept as BT120 for consistency, or just '장기'
                    'data': period_df['long_cum_return_pct'].tolist(),
                    'borderColor': '#3BC1A8'
                })

            # 4. Integrated / Mix (mix_cum_return_pct) -> This is the new Ensemble/Integrated line
            if 'mix_cum_return_pct' in period_df.columns:
                datasets.append({
                    'label': '통합 (Ensemble)',
                    'data': period_df['mix_cum_return_pct'].tolist(),
                    'borderColor': '#f44252'
                })

            all_chart_data[str(period)] = {
                'labels': common_labels,
                'datasets': datasets
            }
            
    except Exception as e:
        print(f"Error reading CSV: {e}")
        # 에러 발생 시 빈 데이터 구조 생성
        for period in holding_periods:
            all_chart_data[str(period)] = {'labels': [], 'datasets': []}

    # 전략별 성과 지표 데이터 (Hardcoded as requested)
    # Data Format: { 'Period': { 'Label': { ...metrics... } } }
    kospi_metric = {'title': '📈 KOSPI (벤치마크)', 'sharpe': '0.45', 'total_return': '9.20%', 'annual_return': '4.50%', 'mdd': '-8.5%', 'eval': '기준 지수'}

    all_strategy_metrics = {
        '20': {
            'KOSPI': kospi_metric,
            '단기 (BT20)': {'title': '🏆 단기 (Short)', 'sharpe': '1.427', 'mdd': '-7.07%', 'total_return': '18.19%', 'annual_return': '8.74%', 'eval': '우수 성과'},
            '장기 (BT120)': {'title': '🥉 장기 (Long)', 'sharpe': '0.107', 'mdd': '-12.14%', 'total_return': '1.10%', 'annual_return': '0.55%', 'eval': '보통'},
            '통합 (Ensemble)': {'title': '🥈 혼합 (Mix)', 'sharpe': '0.689', 'mdd': '-7.52%', 'total_return': '8.13%', 'annual_return': '3.99%', 'eval': '안정적'}
        },
        '40': {
            'KOSPI': kospi_metric,
            '단기 (BT20)': {'title': '🏆 단기 (Short)', 'sharpe': '0.667', 'mdd': '-12.14%', 'total_return': '8.54%', 'annual_return': '4.18%', 'eval': '양호'},
            '장기 (BT120)': {'title': '🥉 장기 (Long)', 'sharpe': '1.084', 'mdd': '-8.52%', 'total_return': '12.39%', 'annual_return': '6.02%', 'eval': '우수 성과'},
            '통합 (Ensemble)': {'title': '🥈 혼합 (Mix)', 'sharpe': '0.912', 'mdd': '-8.64%', 'total_return': '8.47%', 'annual_return': '4.15%', 'eval': '안정적'}
        },
        '60': {
            'KOSPI': kospi_metric,
            '단기 (BT20)': {'title': '🏆 단기 (Short)', 'sharpe': '0.274', 'mdd': '-11.31%', 'total_return': '7.13%', 'annual_return': '3.51%', 'eval': '보통'},
            '장기 (BT120)': {'title': '🥉 장기 (Long)', 'sharpe': '0.453', 'mdd': '-11.74%', 'total_return': '3.07%', 'annual_return': '1.52%', 'eval': '보통'},
            '통합 (Ensemble)': {'title': '🥈 혼합 (Mix)', 'sharpe': '0.115', 'mdd': '-12.01%', 'total_return': '2.99%', 'annual_return': '1.48%', 'eval': '보통'}
        },
        '80': {
            'KOSPI': kospi_metric,
            '단기 (BT20)': {'title': '🏆 단기 (Short)', 'sharpe': '-0.005', 'mdd': '-13.59%', 'total_return': '0.55%', 'annual_return': '0.27%', 'eval': '저조'},
            '장기 (BT120)': {'title': '🥉 장기 (Long)', 'sharpe': '0.622', 'mdd': '-10.36%', 'total_return': '5.78%', 'annual_return': '2.85%', 'eval': '양호'},
            '통합 (Ensemble)': {'title': '🥈 혼합 (Mix)', 'sharpe': '0.371', 'mdd': '-11.08%', 'total_return': '4.56%', 'annual_return': '2.25%', 'eval': '보통'}
        },
        '100': {
            'KOSPI': kospi_metric,
            '단기 (BT20)': {'title': '🏆 단기 (Short)', 'sharpe': '-0.312', 'mdd': '-14.55%', 'total_return': '-4.36%', 'annual_return': '-2.21%', 'eval': '저조'},
            '장기 (BT120)': {'title': '🥉 장기 (Long)', 'sharpe': '1.008', 'mdd': '-7.80%', 'total_return': '14.82%', 'annual_return': '7.16%', 'eval': '우수 성과'},
            '통합 (Ensemble)': {'title': '🥈 혼합 (Mix)', 'sharpe': '0.258', 'mdd': '-11.09%', 'total_return': '3.76%', 'annual_return': '1.86%', 'eval': '보통'}
        },
        '120': {
            'KOSPI': kospi_metric,
            '단기 (BT20)': {'title': '🏆 단기 (Short)', 'sharpe': '-0.356', 'mdd': '-15.19%', 'total_return': '-2.43%', 'annual_return': '-1.22%', 'eval': '저조'},
            '장기 (BT120)': {'title': '🥉 장기 (Long)', 'sharpe': '1.576', 'mdd': '-5.58%', 'total_return': '19.05%', 'annual_return': '8.99%', 'eval': '매우 우수'},
            '통합 (Ensemble)': {'title': '🥈 혼합 (Mix)', 'sharpe': '0.509', 'mdd': '-10.35%', 'total_return': '11.13%', 'annual_return': '5.42%', 'eval': '우수 성과'}
        }
    }

    print("all_chart_data:", all_chart_data)  # 디버그용

    # 시장 지표 가져오기
    market_indices = get_market_indices()
    
    return render_template('index.html', 
                            all_chart_data=all_chart_data,
                            all_strategy_metrics=all_strategy_metrics,
                            # Defensive: Pass compatibility variables to avoid Jinja errors if template is cached or has lingering refs
                            graph_labels=[],
                            graph_datasets=[],
                            strategy_metrics={},
                            input_date=input_date, 
                            short_dict=short_dict, 
                            long_dict=long_dict,
                            integrated_dict=integrated_dict,
                            market_indices=market_indices)




@app.route('/glossary')
def glossary():
    # 로그인 보호
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('glossary.html')

@app.route('/impact/<indicator>')
def impact_detail(indicator):
    # 로그인 보호
    if 'user' not in session:
        return redirect(url_for('login'))

    # 어떤 랭킹 테이블에서 왔는지(단기/장기/통합), 선택 날짜(선택사항)
    model = request.args.get('model', 'integrated')
    date = request.args.get('date', '')
    selected_topics_str = request.args.get('selected_topics', '')
    selected_topics = [t.strip() for t in selected_topics_str.split(',')] if selected_topics_str else []

    model_label_map = {
        'short': '단기랭킹',
        'long': '장기랭킹',
        'integrated': '통합랭킹'
    }
    model_label = model_label_map.get(model, '통합랭킹')

    # (index.html과 동일한) 아이콘/색상/타이틀 매핑
    icon_map = {
        'technical': {'icon': 'bar-chart-2', 'color': '#B95E82', 'title': '기술적 지표'},
        'news': {'icon': 'newspaper', 'color': '#4363D8', 'title': '뉴스'},
        'value': {'icon': 'trending-up', 'color': '#E6194B', 'title': '가치'},
        'profitability': {'icon': 'coins', 'color': '#FFE119', 'title': '수익성'},
        'esg': {'icon': 'leaf', 'color': '#3CB44B', 'title': 'ESG'},
        'others': {'icon': 'more-horizontal', 'color': '#F58231', 'title': '기타'}
    }

    # 설명 컨텐츠 (원하는 만큼 문장을 더 추가해도 됨)
    explanations = {
        'technical': {
            'headline': '가격·거래량 기반 신호로 “지금 시장이 무엇에 반응하는지”를 빠르게 반영해요.',
            'why': [
                '단기적으로는 **추세(모멘텀)·반전·변동성·거래대금(유동성)** 같은 신호가 “다음 며칠~몇 주” 수익률에 영향을 주는 경우가 많아요.',
                '수급이 강하게 붙거나(거래량 급증) 변동성이 확대되면, 랭킹 모델은 “기회(상승 추세)” 혹은 “리스크(과열·급락)”로 해석할 수 있어요.'
            ],
            'how_used': [
                '단기랭킹에서 상대적으로 비중이 커지기 쉬워요. (뉴스/수급 변화가 곧바로 가격에 반영되기 때문)',
                '장기랭킹에서는 노이즈가 커질 수 있어서 “추세 확인용 보조 신호”로 쓰는 게 안정적이에요.'
            ],
            'tips': [
                '한 번의 스파이크보다 **여러 날/주에 걸친 일관된 추세**가 더 신뢰도가 높아요.',
                '급등주일수록 “되돌림(리버설)”이 나올 수 있어 **리스크 관리(손절/분산)**가 중요해요.'
            ]
        },
        'news': {
            'headline': '뉴스는 “새 정보(서프라이즈)”가 주가에 반영되는 속도를 가장 직접적으로 보여줘요.',
            'why': [
                '실적, 계약, 규제, 사건/사고 같은 이벤트는 투자자 기대를 바꾸고 **리프라이싱**을 만들어요.',
                '특히 감성(호재/악재)과 강도(중요도)가 높을수록 단기 수익률 변동(급등/급락)으로 이어질 수 있어요.'
            ],
            'how_used': [
                '단기랭킹: 이벤트 드리븐(발표/공시) 영향이 커서 상위권 변동을 크게 만들 수 있어요.',
                '장기랭킹: “기업 펀더멘털을 바꾸는 뉴스(사업 구조/규제/지속가능성)”는 장기에도 의미가 있어요.'
            ],
            'tips': [
                '뉴스는 **시점**이 핵심이에요. (발표 직후 1~3일 반응 vs. 한 달 이상 구조적 변화)',
                '단발성 이슈인지, 반복적으로 누적되는 이슈인지 구분해 해석해요.'
            ]
        },
        'value': {
            'headline': '가치(밸류)는 “싸게 샀는지/비싸게 샀는지”가 장기 수익률에 연결된다는 가정이에요.',
            'why': [
                'PER/PBR/EV·EBITDA 같은 지표는 장기적으로 **평균회귀(Mean Reversion)**가 나타날 수 있어요.',
                '시장 상황이 안정되면 “저평가 → 재평가” 흐름이 랭킹에 강하게 반영될 수 있어요.'
            ],
            'how_used': [
                '장기랭킹에서 가장 설명력이 커지기 쉬워요. (밸류 프리미엄은 보통 기간이 길수록 관측)',
                '단기랭킹에서는 오히려 “싼데 더 싸지는” 구간이 있을 수 있어 보조적으로 해석해요.'
            ],
            'tips': [
                '밸류는 “왜 싼지”가 중요해요. **구조적 하락(업황) vs. 일시적 이슈**를 구분해요.',
                '부채/현금흐름 같이 재무안정성과 함께 보면 실패 확률을 줄일 수 있어요.'
            ]
        },
        'profitability': {
            'headline': '수익성(퀄리티)은 “돈을 꾸준히 잘 버는 기업”이 장기적으로 강하다는 관점이에요.',
            'why': [
                'ROE/영업이익률/매출총이익률 같은 지표는 기업의 **경쟁력·가격결정력·효율성**을 반영해요.',
                '수익성이 안정적이면 경기 변동에도 버티기 쉬워 **리스크가 낮고 복리(컴파운딩)**가 잘 일어나요.'
            ],
            'how_used': [
                '장기랭킹에서 특히 유리해요. (꾸준한 실적이 누적되며 주가에 반영)',
                '단기랭킹에서도 “실적 서프라이즈”가 있으면 수익성이 함께 상위 요인으로 뜰 수 있어요.'
            ],
            'tips': [
                '단기 실적 급증보다 **여러 분기/연도에 걸친 안정성**을 확인하면 좋아요.',
                '같은 업종 내에서 비교(상대평가)하면 왜 강한지 설명이 쉬워요.'
            ]
        },
        'esg': {
            'headline': 'ESG는 “규제·평판·비용·자본조달” 리스크를 줄이는 요소로 해석될 때가 많아요.',
            'why': [
                '환경/사회/지배구조 이슈는 벌금, 소송, 규제, 공급망 차질처럼 **현금흐름에 직접 타격**을 줄 수 있어요.',
                'ESG 개선은 기관/연기금 자금 유입(수급)과 연결되어 **자본비용(할인율)**에 영향을 줄 수 있어요.'
            ],
            'how_used': [
                '장기랭킹: 리스크 프리미엄과 비용 구조에 영향을 주기 때문에 장기에서 의미가 커질 수 있어요.',
                '단기랭킹: “논란/사건” 같은 급격한 ESG 이슈는 단기 급락(리스크)으로도 반영될 수 있어요.'
            ],
            'tips': [
                'ESG는 단일 점수보다 **이슈의 방향(개선/악화)과 강도**가 더 중요할 때가 많아요.',
                '업종 특성(예: 제조/에너지/플랫폼)에 따라 중요한 ESG 항목이 달라요.'
            ]
        },
        'others': {
            'headline': '기타(others)는 위 5개로 묶기 어려운 보조 신호들이에요.',
            'why': [
                '예: 업종/거시(금리·환율) 민감도, 리스크 지표, 특수 이벤트 등',
                '특정 시장 국면에서는 “기타”가 갑자기 중요해질 수 있어요. (예: 환율 급등, 금리 급변)'
            ],
            'how_used': [
                '메인 요인의 “설명력”이 떨어질 때 보완 역할을 해요.',
                '특정 날짜에만 튀는 경우가 많아서, 맥락(시장 상황)과 함께 보는 게 좋아요.'
            ],
            'tips': [
                '같은 날 시장 전체 이슈(금리/환율/정책)를 같이 확인하면 이해가 빨라요.'
            ]
        }
    }

    ticker = request.args.get('ticker', '')

    # -- [START] Specific Logic for 2023-06-21 Demo --
    if date == '2023-06-21':
        specific_explanations = {}
        
        # 1. Korea Electric Power (Short-Term #1)
        # Check ticker to ensure we don't show this for other short-term stocks
        if model == 'short' and ('한국전력' in ticker or '015760' in ticker):
            specific_explanations = {
                'news': {
                    'headline': '📈 뉴스 감성 및 언급량 폭발 (기여도 35.0% - Top 1)',
                    'why': [
                        '**전기요금 인상, 에너지 정책** 등 공기업 관련 뉴스가 시장 관심을 집중시킴.',
                        '긍정적 뉴스 감성과 높은 언급량이 단기 매수 심리를 강력하게 자극함.'
                    ],
                    'how_used': [
                        '단기 전략에서 뉴스는 시장 참여자들의 심리를 반영하는 가장 빠른 지표.',
                        '호재성 뉴스의 빈도 증가는 단기 추세 강화 신호로 해석.'
                    ],
                    'tips': [
                        '시장 관심도가 높을 때 변동성도 함께 커질 수 있으니 주의.',
                        '뉴스의 지속성(단발성 vs 추세)을 함께 체크하세요.'
                    ]
                },
                'profitability': {
                    'headline': '💰 안정적 수익 구조 재평가 (기여도 25.0% - Top 2)',
                    'why': [
                        '공기업으로서의 **안정적인 현금 흐름**과 재무 건전성이 부각됨.',
                        '시장 불안정 시기에 확실한 수익 기반을 가진 종목으로 수급 쏠림 현상.'
                    ],
                    'how_used': [
                        '단기 랭킹에서도 "기초 체력"이 튼튼한 종목이 반등 탄력이 좋음.',
                        '재무 리스크가 낮은 종목은 하락장에서도 방어력이 우수.'
                    ],
                    'tips': [
                        '공기업 특성상 이익 개선 이슈(요금 인상 등)와 함께 보면 효과적.'
                    ]
                },
                'technical': {
                    'headline': '📊 낮은 변동성, 안정적 트레이딩 (기여도 20.0% - Top 3)',
                    'why': [
                        '시장 평균 대비 현저히 낮은 변동성 지표(Volatility)를 기록.',
                        '**공기업 특유의 주가 안정성**이 단기 트레이딩 리스크를 낮춰줌.'
                    ],
                    'how_used': [
                        '급등락이 적어 예측 가능한 범위 내에서 트레이딩 가능.',
                        '시장 충격 발생 시 상대적으로 덜 민감하여 포트폴리오 안정화에 기여.'
                    ],
                    'tips': [
                        '변동성이 낮을 때는 추세 추종보다는 박스권 매매나 안정적 보유가 유리.'
                    ]
                },
                'value': {
                    'headline': '💎 탄탄한 밸류에이션 매력 (기여도 10.0%)',
                    'why': [
                        'PBR, PER 등 전통적 가치 지표가 저평가 영역에 위치.',
                        '거래대금이 활발히 유입되며 저평가 해소 기대감 상승.'
                    ],
                    'how_used': ['단기 테마성 상승에도 밸류에이션 부담이 없어 추가 상승 여력 제공.'],
                    'tips': ['기관/외국인 수급과 함께 밸류 재평가가 일어나는지 확인.']
                }
            }
            
        # 2. Samsung Electronics (Long-Term #1)
        elif model == 'long' and ('삼성전자' in ticker or '005930' in ticker):
            specific_explanations = {
                'profitability': {
                    'headline': '👑 압도적 글로벌 수익성 (기여도 35.0% - Top 1)',
                    'why': [
                        '글로벌 반도체 시장 지배력을 바탕으로 한 **강력한 현금 창출 능력(EBITDA, ROE)**.',
                        '경기 사이클 변동에도 견고한 이익 체력을 증명.'
                    ],
                    'how_used': [
                        '장기 랭킹의 핵심은 "결국 돈을 잘 버는가"입니다.',
                        '높은 수익성은 장기 우상향 주가 흐름의 가장 확실한 보증 수표.'
                    ],
                    'tips': [
                        '절대적 이익 규모뿐만 아니라 이익률의 추세적 변화를 주목하세요.'
                    ]
                },
                'technical': {
                    'headline': '📈 장기적 추세의 안정성 (기여도 30.0% - Top 2)',
                    'why': [
                        '단기 등락을 넘어선 **장기 이동평균선의 정배열** 및 안정적 추세 유지.',
                        '과도한 변동성 없이 꾸준히 저점을 높여가는 이상적인 우상향 패턴.'
                    ],
                    'how_used': [
                        '장기 투자에서 Timing 리스크를 줄여주는 핵심 지표.',
                        '펀더멘털이 좋은 기업의 기술적 안정성은 장기 보유의 심리적 안정감 제공.'
                    ],
                    'tips': [
                        '월봉/주봉 단위의 큰 추세를 확인하는 것이 중요.'
                    ]
                },
                'esg': {
                    'headline': '🌱 지속가능경영 리더십 (기여도 20.0% - Top 3)',
                    'why': [
                        '환경(E), 사회(S), 지배구조(G) 전 영역에서 글로벌 스탠다드 부합.',
                        '특히 글로벌 기관 투자자들이 중시하는 **지속가능성 리스크**가 낮음.'
                    ],
                    'how_used': [
                        '장기 포트폴리오에서 "돌발 악재(오너 리스크, 환경 규제)"를 필터링하는 역할.',
                        '외국인 자금 유입의 필수 선결 조건.'
                    ],
                    'tips': [
                        'ESG는 단순 점수보다 개선 방향성(특히 지배구조)이 주가에 더 큰 영향.'
                    ]
                },
                'value': {
                    'headline': '⚖️ 합리적인 밸류에이션 (기여도 10.0%)',
                    'why': [
                        '글로벌 경쟁사 대비 부담 없는 밸류에이션 구간.',
                        '탄탄한 실적 기반 위에 형성된 적정 주가 수준.'
                    ],
                    'how_used': ['장기 보유 시 밸류에이션 리스크(거품 붕괴) 걱정 없이 투자 가능.'],
                    'tips': ['산업 평균 대비 프리미엄/할인 요인을 감안하여 판단.']
                }
            }

        # Merge/Override specific explanations into the standard ones
        # Only override keys that exist in specific_explanations
        for k, v in specific_explanations.items():
            explanations[k] = v

    # -- [END] Specific Logic --

    if indicator not in explanations:
        indicator = 'others'

    meta = icon_map.get(indicator, icon_map['others'])
    info = explanations.get(indicator, explanations['others'])

    # index로 돌아가기 링크 (date가 있을 때만 유지)
    back_href = url_for('index')
    if date:
        back_href = f"{back_href}?date={date}"

    categories = ['technical', 'news', 'value', 'profitability', 'esg', 'others']
    if selected_topics:
        categories = [c for c in categories if c in selected_topics]

    template = r'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      {% include 'refer/header.html' %}
      <style>
        .impact-hero {
          background: linear-gradient(135deg, rgba(102,126,234,0.85), rgba(118,75,162,0.85));
          border-radius: 18px;
          padding: 20px 22px;
          color: #fff;
          box-shadow: 0 10px 30px rgba(0,0,0,0.22);
        }
        .impact-chip {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 10px 12px;
          border-radius: 999px;
          text-decoration: none;
          background: rgba(255,255,255,0.12);
          color: #fff;
          margin: 6px 6px 0 0;
          transition: transform 120ms ease, background-color 120ms ease, box-shadow 120ms ease;
        }
        .impact-chip:hover { background: rgba(255,255,255,0.18); transform: translateY(-1px); }
        .impact-chip.active { background: rgba(255,255,255,0.26); box-shadow: inset 0 0 0 1px rgba(255,255,255,0.25); }
        .impact-card { border-radius: 18px; overflow: hidden; }
        .impact-section h5 { font-weight: 800; }
        .impact-section ul { margin-bottom: 0; }
        .impact-section li { margin: 6px 0; }
      </style>
    </head>

    <body>
      <div class="container-scroller">
        {% include 'refer/sidebar.html' %}

        <div class="container-fluid page-body-wrapper">
          {% include 'refer/headbar.html' %}

          <div class="main-panel">
            <div class="content-wrapper">

              <div class="d-flex align-items-center justify-content-between mb-3">
                <div>
                  <h3 class="mb-1" style="font-weight: 900;">영향(지표) 설명</h3>
                  <div class="text-muted" style="font-size: 0.95rem;">
                    현재: <b>{{ model_label }}</b>{% if date %} · 날짜: <b>{{ date }}</b>{% endif %}
                  </div>
                </div>
                <a href="{{ back_href }}" class="btn btn-outline-light" style="border-radius: 999px;">
                  <i class="mdi mdi-arrow-left"></i> 랭킹으로
                </a>
              </div>

              <div class="impact-hero mb-4">
                <div class="d-flex align-items-start justify-content-between flex-wrap" style="gap: 12px;">
                  <div class="d-flex align-items-start" style="gap: 14px;">
                    <div style="width: 48px; height: 48px; border-radius: 14px; background: rgba(255,255,255,0.18); display:flex; align-items:center; justify-content:center;">
                      <i data-lucide="{{ meta.icon }}" style="width: 26px; height: 26px; color: {{ meta.color }};"></i>
                    </div>
                    <div>
                      <div style="font-size: 0.95rem; opacity: 0.9;">{{ meta.title }}</div>
                      <div style="font-size: 1.35rem; font-weight: 900; line-height: 1.2;">{{ info.headline }}</div>
                    </div>
                  </div>

                  <div class="d-flex flex-wrap" style="gap: 8px;">
                    {% for cat in categories %}
                      {% set m = icon_map.get(cat, icon_map['others']) %}
                      <a class="impact-chip {% if cat == indicator %}active{% endif %}"
                         href="{{ url_for('impact_detail', indicator=cat) }}?model={{ model }}{% if date %}&date={{ date }}{% endif %}&selected_topics={{ selected_topics_str }}&ticker={{ ticker }}">
                        <i data-lucide="{{ m.icon }}" style="width: 18px; height: 18px; color: {{ m.color }};"></i>
                        <span style="font-weight: 700;">{{ m.title }}</span>
                      </a>
                    {% endfor %}
                  </div>
                </div>
              </div>

              <div class="row">
                <div class="col-lg-7 grid-margin stretch-card">
                  <div class="card impact-card">
                    <div class="card-body impact-section">
                      <h5 class="mb-3">왜 랭킹에 영향을 많이 줬을까?</h5>
                      <ul>
                        {% for line in info.why %}
                          <li>{{ line | safe }}</li>
                        {% endfor %}
                      </ul>
                    </div>
                  </div>
                </div>

                <div class="col-lg-5 grid-margin stretch-card">
                  <div class="card impact-card">
                    <div class="card-body impact-section">
                      <h5 class="mb-3">단기/장기에서 어떻게 다르게 해석해?</h5>
                      <ul>
                        {% for line in info.how_used %}
                          <li>{{ line | safe }}</li>
                        {% endfor %}
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              <div class="row">
                <div class="col-12 grid-margin stretch-card">
                  <div class="card impact-card">
                    <div class="card-body impact-section">
                      <h5 class="mb-3">해석 팁</h5>
                      <ul>
                        {% for line in info.tips %}
                          <li>{{ line | safe }}</li>
                        {% endfor %}
                      </ul>
                      <div class="text-muted mt-3" style="font-size: 0.9rem;">
                        * 이 페이지는 “아이콘(영향)”을 클릭했을 때 지표군의 의미를 빠르게 설명하기 위한 요약이에요.
                      </div>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>

      {% include 'refer/script.html' %}
      <script>
        lucide.createIcons();
      </script>
    </body>
    </html>
    '''

    return render_template_string(
        template,
        indicator=indicator,
        model=model,
        model_label=model_label,
        date=date,
        meta=meta,
        info=info,
        categories=categories,
        icon_map=icon_map,
        back_href=back_href,
        selected_topics_str=selected_topics_str,
        ticker=ticker
    )





# 웹서버를 실행 
if __name__ == '__main__':
    # debug -> debug모드로 실행 -> 파일이 수정될때마다 웹서버가 재시작이 자동 (기본값은 False)
    app.run(debug=True)

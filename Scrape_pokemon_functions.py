import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import numpy as np
import re

base_url = 'https://play.limitlesstcg.com'

def create_1_df(url):
    r = requests.get(url)
    html = r.text
    soup = BeautifulSoup(html,'html.parser')
    rows = soup.select('tr')
    deck, deck_links, count, share, score, win = [], [], [], [], [], []
    for row in rows:
        one_row = row.select('td')
        for index, data in enumerate(one_row):
            if index == 2:
                deck.append(data.text)
                deck_links.append(data.a['href'])
            if index == 3:
                count.append(data.text)
            if index == 4:
                share.append(data.text)
            if index == 5:
                score.append(data.text)
            if index == 6:
                win.append(data.text)
    df = pd.DataFrame({'Deck':deck,
                  'Count':count,
                  'Share':share,
                  'Score':score,
                  'Win_Percentage':win,
                    'Deck_links':deck_links})
    return df

def cook_soup(url):
    base_url = 'https://play.limitlesstcg.com'
    r = requests.get(base_url + url)
    html = r.text
    soup = BeautifulSoup(html, 'html.parser')
    return soup

def cook_soups(link_list):
    soups = []
    for link in link_list:
        soup = cook_soup(link)
        soups.append(soup)
    return soups

def create_2_df(soup):
    rows = soup.select('tr')
    player, date, tournament, tournament_url, place, score, lst_url = [], [], [], [], [], [], []
    deck = [soup.select('div[class="name"]')[0].text for i in range(len(rows)-1)]
    
    for row in rows:
        one_row = row.select('td')
        for index, data in enumerate(one_row):
            if index == 0:
                player.append(data.text)
            if index == 1:
                tournament.append(data.text)
                tournament_url.append(data.a['href'])
            if index == 2:
                date.append(data.a['data-time'])
            if index == 3:
                place.append(data.text)
            if index == 4:
                score.append(data.text)
            if index == 5:
                try:
                    lst_url.append(data.a['href'])
                except TypeError:
                    lst_url.append('Decklist not available')
                
    df = pd.DataFrame({'Deck':deck,
                        'Player':player,
                        'Date':date,
                        'Tournament':tournament,
                        'Place':place,
                        'Score':score,
                        'Decklist_url':lst_url,
                          'Tournament_url':tournament_url})
    regex = re.compile(r"(\d{0,4})[a-z]{2} of (\d{0,4})")
    placement, player_total = [], []
    for row in df['Place']:
        try:
            placement.append(int(re.search(regex, row)[1]))
        except TypeError:
            placement.append(None)
        try:
            player_total.append(int(re.search(regex, row)[2]))
        except TypeError:
            player_total.append(None)
    df['Placement'] = placement
    df['Player_Total'] = player_total
    df.drop('Place',axis=1,inplace=True)
    df['Date'] = [datetime.date.fromtimestamp(int(date)/1000) for date in df['Date']]
    #strftime("%B %d, %Y")
    df = df[['Deck', 'Player', 'Date', 'Tournament', 'Placement', 'Player_Total', 'Score', 'Decklist_url', 'Tournament_url']]
    return df

def create_2_dfs(soups):
    df_list = []
    for soup in soups:
        df = create_2_df(soup)
        df.dropna(inplace=True)
        df_list.append(df)
    df = pd.concat(df_list).reset_index(drop=True)
    return df

def scrape_decklist(url):
    request = requests.get(url)
    html = request.text
    soup = BeautifulSoup(html, 'html.parser')
    number, card, version = [], [], []
    regex = re.compile(r"([12]) ([\w'é\-\.]*(?: [\wé\-\.]*)?(?: [\wé\-\.]*)?) ?(\([\w-]*\))?")
    for a in soup.select('a[target="_blank"]'):
        match = re.search(regex, a.text)
        if match is not None:
            number.append(match[1])
            card.append(match[2].strip())
            if match[3] is None:
                version.append('NA')
            else:
                version.append(match[3])
    df = pd.DataFrame({'Amount':number,
                'Card':card,
                'Version':version})
    return df

def add_decklist_column(link_list, df):
    n, length = 0, len(link_list)
    keys, decklists = [], []
    for index, link in enumerate(df['Decklist_url']):
        keys.append(index)
        if link != 'Decklist not available':
            decklist = scrape_decklist(base_url + link)
            decklists.append(decklist)
        else:
            decklists.append('No decklist')
        n += 1
        if n % 50 == 0:
            print(f"{(n / length)*100} %")
    df['Decklists'] = decklists
    return df

def convert_to_json(series):
    new_series = []
    for lst in series:
        if type(lst) != str:
            lst = lst.to_json()
            new_series.append(lst)
        else:
            new_series.append(lst)
    return new_series

def get_bools(column, pokemon_string):
    bools = []
    for decklist in column:
        if decklist.find(pokemon_string) != -1:
            bools.append(True)
        else:
            bools.append(False)
    return bools

def create_finishes_df(df):
    new = pd.DataFrame({'Finishes':['Top 64',
                    'Top 16',
                    'Top 8',
                    'Top 4',
                    '2nd Place',
                    'Tournament Wins'],
                        'Count':[len(df),len(df[df['Placement'] <= 16]),
                                   len(df[df['Placement'] <= 8]),
                                       len(df[df['Placement'] <= 4]),
                                           len(df[df['Placement'] <= 2]),
                                               len(df[df['Placement'] <= 1])]})
    return new

def filter_top_finishes(df, pokemon):
    df1 = df[df['Decklists'].str.contains(pokemon)]
    df2 = df1[(df1['Player_Total'] >= 200) & (df1['Placement'] <= 64)].sort_values(['Placement','Player_Total'], ascending=[True, False])
    return df2

def make_score(df):
    df1 = create_finishes_df(df)
    score = df1['Count'][1] * 3
    score += df1['Count'][2] * 6
    score += df1['Count'][3] * 10
    score += df1['Count'][4] * 15
    score += df1['Count'][5] * 25
    score += df1['Count'][0]
    return score

def power_ranking_table(df, ex_list):
    expansions = ['Genetic Apex','Mythical Island','Space-Time Smackdown','Triumphant Light',
             'Shining Revelry','Celestial Guardians','Extradimensional Crisis',
             'Eevee Grove','Wisdom of Sea and Sky','Secluded Springs']
    expansion_modifiers = [.3,.38,.45,.53,.61,.69,.77,.85,.93,1]
    all_poke_scores = []
    for name in ex_list:
        one_poke_score = 0
        step2 = filter_top_finishes(df, name)
        for i in range(len(expansions)):
            step3 = step2[step2['Expansion'] == expansions[i]]
            step4_getscore = make_score(step3)
            step5_modify = step4_getscore * expansion_modifiers[i]
            one_poke_score += step5_modify
        all_poke_scores.append(one_poke_score)
    maxs, mins = max(all_poke_scores), min(all_poke_scores)
    all_poke_scores_normalized = [round(((score / (maxs - mins)) * 100),2) for score in all_poke_scores]
    ex_list_to_change = ex_list.copy()
    ex_list_to_change[ex_list.index('A1-36')] = 'Charizard ex: A1'
    ex_list_to_change[ex_list.index('A2b-10')] = 'Charizard ex: A2b'
    ex_list_to_change[ex_list.index('A1-96')] = 'Pikachu ex: A1'
    ex_list_to_change[ex_list.index('A2b-22')] = 'Pikachu ex: A2b'
    scores = pd.DataFrame({'Pokémon':ex_list_to_change,
                           'Score':all_poke_scores_normalized})
    scores = scores.sort_values('Score',ascending=False).reset_index(drop=True)
    return scores

def make_interpolated_table(df, ex_list):
    expansions = ['Genetic Apex','Mythical Island','Space-Time Smackdown','Triumphant Light',
                 'Shining Revelry','Celestial Guardians','Extradimensional Crisis',
                 'Eevee Grove','Wisdom of Sea and Sky','Secluded Springs']
    expansion_modifiers = [.3,.38,.45,.53,.61,.69,.77,.85,.93,1]
    ex_list_to_change = ex_list.copy()
    ex_list_to_change[ex_list.index('A1-36')] = 'Charizard ex: A1'
    ex_list_to_change[ex_list.index('A2b-10')] = 'Charizard ex: A2b'
    ex_list_to_change[ex_list.index('A1-96')] = 'Pikachu ex: A1'
    ex_list_to_change[ex_list.index('A2b-22')] = 'Pikachu ex: A2b'
    unnormalized_df = pd.DataFrame({'Pokémon':ex_list_to_change})
    for i in range(len(expansions)):
        unnormalized_score = []
        for name in ex_list:
            step2 = filter_top_finishes(df, name)
            step3 = step2[step2['Expansion'] == expansions[i]]
            step4_getscore = make_score(step3)
            unnormalized_score.append(round(step4_getscore*expansion_modifiers[i],2))
        unnormalized_df[f'{expansions[i]}'] = unnormalized_score
    
    unnormalized_df['Sum'] = [unnormalized_df.iloc[row].iloc[1:].sum() for row in range(len(unnormalized_df))]
    normalized_df = unnormalized_df.copy()
    maxs, mins = max(unnormalized_df['Sum']), min(unnormalized_df['Sum'])
    normalized_df.drop('Sum',axis=1,inplace=True)
    for column in unnormalized_df[expansions]:
        columns_scores = []
        for cell in unnormalized_df[column]:
                normalized_score = (cell / ((maxs - mins))) * 100
                columns_scores.append(normalized_score)
        normalized_df[column] = columns_scores
    
    normalized_sums = normalized_df.copy()
    normalized_sums[expansions] = normalized_sums[expansions].cumsum(axis=1)
    
    interp_all = []
    names = list(normalized_sums['Pokémon'])
    
    for i in range(len(normalized_sums)):
        interp_all.append(normalized_sums.iloc[i][1:])
    
    expansion_dates = pd.DatetimeIndex(['2024-10-30','2024-12-17', '2025-1-30', '2025-2-28', '2025-3-27', '2025-4-30',
     '2025-5-29', '2025-6-25', '2025-7-30', '2025-8-28'])
    
    times_x = []
    scores_y = []
    for i in range(len(interp_all)):
        interp_all[i].index = expansion_dates
        interp_all[i] = interp_all[i].resample("1D",origin='start').last().infer_objects(copy=False).interpolate()
        times_x.append(np.arange(0,len(interp_all[i])))
        scores_y.append(np.array(list(interp_all[i])))
    
    interpolated = pd.DataFrame(scores_y,columns=times_x[0])
    interpolated.insert(0,'Pokémon',names)
    
    return interpolated

def filter_nonex_frame(df, cardid):
    indices = []
    for i in range(len(df['Decklists'])):
        f = df['Decklists'][i].find(f'({cardid})')
        if f != -1:
            indices.append(i)
    return df.iloc[indices]

def easy_decklist_filter(df, cardid):
    regex = re.compile(r'A[1234][ab]?-\d{1,3}')
    if re.match(regex, cardid):
        df = filter_nonex_frame(df, cardid)
    else:
        df = df[df['Decklists'].str.contains(cardid)]
    return df.reset_index(drop=True)

def get_partners(df, pokemon):
    regex = re.compile(r"([\w\-']+ ?(?:ex)?) ?([\w-]+ ?(?:ex)?)?")
    partners = []
    filtered = df[df['Deck'].str.contains(pokemon)]
    for deck in filtered['Deck']:
        matches = re.match(regex, deck)
        for i in (1,2):
            if matches[i] != pokemon:
                if matches[i] is not None:
                    partners.append(matches[i].strip())
                else:
                    partners.append(f"Solo {pokemon}")
    partners = pd.Series(partners).value_counts().head(5)
    partners = pd.DataFrame(partners).reset_index().rename(columns={'index':'Partner','count':'Count'})
    return partners
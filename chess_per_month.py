import requests
import matplotlib.pyplot as plt
import matplotlib.dates
from tqdm import tqdm
import sys

handle = None
token = None

# read in username and optional token from sys.argv
if len(sys.argv) == 1:
    print('Usage: python chess_per_month.py <username> <optional OAuth2 token> \n\n Downloading games with an OAuth2 token is 2-3 times faster!')
    exit()
else:
    handle = sys.argv[1]

if len(sys.argv) >= 3:
    token = sys.argv[2]

# Helper functions to extract time taken from games
"""
Converts "hh:mm:ss" to seconds
"""
def clockToSeconds(clock):
    h = clock.split(':')
    return 3600*int(h[0])+60*int(h[1])+int(h[2])

"""
Calculates time used during a game

Arguments: string of the format "initial+increment" and the moves of the game with clock comments
"""
def time_used(time_control, game):
    if time_control == '-':
        return 0
    startsecs = int(time_control[:time_control.find('+')])
    increment = int(time_control[time_control.find('+')+1:])
    tmp = game[:game.rfind('.')]
    n_white_moves = int(tmp[tmp.rfind(' ')+1:])

    if game.find('%clk', game.find('%clk', game.rfind('.'))+1) == -1:
        n_black_moves = n_white_moves - 1
    else:
        n_black_moves = n_white_moves
    
    if n_black_moves == 0:
        return 0
    
    tot_time = 2*startsecs + increment * (n_black_moves+n_white_moves)
    final_clock_total = clockToSeconds(game[game.rfind('%clk')+5:game.rfind(']')])
    tmp = game[:game.rfind('%clk')]
    final_clock_total += clockToSeconds(tmp[tmp.rfind('%clk')+5:tmp.rfind(']')])
    return max(0, tot_time-final_clock_total)

# Helper functions to calculate next and previous months from a given month
def nextmonth(date):
    if date[5:] == '12':
        print(date, int(date[:4])+1)
        return str(int(date[:4])+1) + '.01'
    else:
        return date[:5] + ('%02d' % (int(date[5:])+1))

def prevmonth(date):
    if date[5:] == '01':
        return str(int(date[:4])-1) + '.12'
    else:
        return date[:5] + ('%02d' % (int(date[5:])-1))

# get total number of games, prepare progress bar
tot_games = requests.get('https://lichess.org/api/user/%s' % handle).json()['count']['all']
bar = tqdm(total=tot_games)

# request games
headers = {}
if token is not None:
    headers['Authorization'] = 'Bearer ' + token
r = requests.get('https://lichess.org/api/games/user/%s?clocks=true' % handle, headers=headers, stream=True)

# details of the current game
current_time_control = None
current_date = None
current_game = None

# total time taken and time taken per month
tot_time = 0
x = []
y = []


for line in r.iter_lines():
    line = line.decode('utf-8')
    
    if line[:12] == '[TimeControl':
        current_time_header = line[14:-2]
    if line[:8] == '[UTCDate':
        current_date = line[10:-5]
    if line != '' and line[0] != '[':
        # game
        current_game = line
        if len(x) == 0:
            x.append(current_date)
            y.append(0)
        elif x[-1] != current_date:
            # there are some months where no games were played between current month and next game
            # note: games are processed in reverse order
            if prevmonth(x[-1]) != current_date:
                x.append(prevmonth(x[-1]))
                y.append(0)
                if x[-1] != nextmonth(current_date):
                    x.append(nextmonth(current_date))
                    y.append(0)
            
            tot_time += y[-1]
        
            x.append(current_date)
            y.append(0)
         
        y[-1] += time_used(current_time_header, current_game)/3600
        bar.update(1)

tot_time += y[-1]
print('Total time on chess: %.2f hours' % (tot_time,))


x = list(map(lambda x: matplotlib.dates.datestr2num(x + '.01'), x))



# use a gray background
ax = plt.axes()
ax.set_facecolor('#E6E6E6')
ax.set_axisbelow(True)

# draw solid white grid lines
plt.grid(color='w', linestyle='solid')

# hide axis spines
for spine in ax.spines.values():
    spine.set_visible(False)
    
    # hide top and right ticks
    ax.xaxis.tick_bottom()
    ax.yaxis.tick_left()

    # lighten ticks and labels
    ax.tick_params(colors='gray', direction='out')
    for tick in ax.get_xticklabels():
        tick.set_color('gray')
        for tick in ax.get_yticklabels():
            tick.set_color('gray')
                    

# plot data
plt.title('Hours of chess per month for /@/%s' % handle )
plt.plot_date(x, y, linestyle='solid')
plt.xlabel('Month')
plt.xticks(rotation=45)
plt.ylabel('Hours of chess')
plt.savefig('%s.png' % handle, dpi=200, bbox_inches='tight', figsize=(8, 6))
plt.show()


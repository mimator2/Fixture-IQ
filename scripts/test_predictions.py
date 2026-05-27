"""
Quick test script to run predictions on several players.
"""
import sys
import json
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.models.predict import predict

players = [
    ('Declan Rice', 'Arsenal'),
    ('Bukayo Saka', 'Arsenal'),
    ('Kevin De Bruyne', 'Manchester City'),
    ('Mohamed Salah', 'Liverpool'),
    ('Erling Haaland', 'Manchester City'),
    ('Virgil van Dijk', 'Liverpool'),
    ('Martin Odegaard', 'Arsenal'),
    ('Rodri', 'Manchester City'),
]

print(f'{"Player":25s} {"Team":18s} {"Risk %":8s} {"Level":15s} {"ACWR":8s}')
print('-' * 75)

for player, team in players:
    r = predict(player_name=player, team_name=team, verbose=False)
    if r:
        acwr = r['signals'].get('acwr_value', 'N/A')
        print(f'{player:25s} {team:18s} {r["fatigue_risk_probability"]*100:6.1f}%  {r["risk_level"]:15s} {str(acwr):8s}')
    else:
        print(f'{player:25s} {team:18s} {"N/A":8s} {"NOT FOUND":15s}')

print('\n\nDetailed JSON for Declan Rice:')
r = predict(player_name='Declan Rice', team_name='Arsenal', verbose=False)
if r:
    print(json.dumps(r, indent=2))

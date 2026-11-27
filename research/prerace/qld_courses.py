"""Queensland course identity map (Batch 18 A3, approved by Damo 27 Nov 2026: "Approve correcting historical course-name matching in
production v2.1.3"). Racing Queensland / TAB meeting names (as in the morning fields) -> the course key used in Queensland tracked history
(runs.parquet 'track'), which carries sponsor names for three courses. Turf and Polytrack at the Sunshine Coast stay separate courses;
a Sunshine Coast meeting is the Polytrack course when its name says Poly or its track condition is Synthetic.
History keys are not changed here (they are what the engines were fitted on); only today's names are mapped onto them."""
import re
HISTORY_KEY = {'Eagle Farm': 'Eagle_Farm', 'Doomben': 'Doomben', 'Ipswich': 'Ipswich', 'Toowoomba': 'Toowoomba', 'Townsville': 'Townsville', 'Rockhampton': 'Rockhampton',
               'Mackay': 'Mackay', 'Dalby': 'Dalby', 'Kilcoy': 'Kilcoy', 'Sunshine Coast': 'Sunshine_Coast', 'Sunshine Coast Poly Track': 'Sunshine_Coast_Poly_Track',
               'Sunshine Coast Poly': 'Sunshine_Coast_Poly_Track', 'Cairns': 'Ladbrokes_Cannon_Park', 'Cannon Park': 'Ladbrokes_Cannon_Park', 'Ladbrokes Cannon Park': 'Ladbrokes_Cannon_Park',
               'Gold Coast': 'TAB_Park_Gold_Coast', 'Aquis Park Gold Coast': 'TAB_Park_Gold_Coast', 'TAB Park Gold Coast': 'TAB_Park_Gold_Coast',
               'Warwick': 'Picklebet_Park_Warwick', 'Picklebet Park Warwick': 'Picklebet_Park_Warwick'}
def history_key(track, condition=None):
    """today's meeting name -> history course key; unknown names fall back to the old rule (spaces -> underscores), never guessed"""
    t = str(track).strip()
    if t.startswith('Sunshine Coast') and re.search(r'(?i)synth|poly', str(condition or '') + ' ' + t): return 'Sunshine_Coast_Poly_Track'
    return HISTORY_KEY.get(t, t.replace(' ', '_'))

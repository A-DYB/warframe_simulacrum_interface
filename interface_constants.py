
NON_USER_MODS = [{'main_type':'damagePerShot_m', 'sub_type':'multishot_multiplier'},
                 {'main_type':'procChance_m', 'sub_type':'multishot_multiplier'},
                 {'main_type':'combineElemental_m', 'sub_type':'indices'}
                 ]

REMAP_MOD_SEARCH = {
                    'Proc Chance': ['Status Chance'],
                    'Magazine Size':['Clip Size'],
                    'Fire Rate':['Attack Speed'],
                    'Reload Time':['Relaod Speed'],
                    'Heat':['Element', 'Elemental', 'Blast', 'Radiation', 'Gas'],
                    'Cold':['Element', 'Elemental', 'Blast', 'Magnetic', 'Viral'],
                    'Electric':['Element', 'Elemental', 'Radiation', 'Magnetic', 'Corrosive'],
                    'Toxin':['Element', 'Elemental', 'Gas', 'Viral', 'Corrosive'],
                    'Blast':['Element', 'Elemental'],
                    'Radiation':['Element', 'Elemental'],
                    'Gas':['Element', 'Elemental'],
                    'Magnetic':['Element', 'Elemental'],
                    'Viral':['Element', 'Elemental'],
                    'Corrosive':['Element', 'Elemental'],
                    'Impact':['Physical'],
                    'Puncture':['Physical'],
                    'Slash':['Physical'],
                    'Faction Damage':['Roar'],
                    'Critical Multiplier':['Critical Damage', 'Crit Mult'],
                    'Critical Chance':['Crit Chance']
}

MOD_MIN_VALUE_MAP = {
                'damagePerShot_m':{"multishot_multiplier":1, "final_multiplier":1},
                'criticalChance_m':{"deadly_munitions":1},
                'criticalMultiplier_m':{"final_multiplier":1},
                'procChance_m':{"multishot_multiplier":1, "final_multiplier":1},
}

DAMAGING_PROC_NAME_INDEX = {"Slash":2, "Heat":3, "Electric":5, "Toxin":6, "Gas":9}

D_INDEX = {'Impact': 0, 'Puncture': 1, 'Slash': 2, 'Heat': 3, 'Cold': 4, 'Electric': 5, 
           'Toxin': 6, 'Blast': 7, 'Radiation': 8, 'Gas': 9, 'Magnetic': 10, 'Viral': 11, 
           'Corrosive': 12, 'Finisher': 13, 'Radiant': 14, 'Sentient': 15, 'Cinematic': 16, 
           'Shield_drain': 17, 'Health_drain': 18, 'Energy_drain': 19, 'Suicide': 20, 'Physical': 21, 
           'Base_elemental': 22, 'Compound_elemental': 23, 'Any': 0, 'Invalid': 24}
INDEX_D = {v:k for k,v in D_INDEX.items()}

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

COMBINABLEDAMAGE_INDEX = {'Blast': 7, 'Radiation': 8, 'Gas': 9, 'Magnetic': 10, 'Viral': 11, 
           'Corrosive': 12}
INDEX_COMBINABLEDAMAGE = {v:k for k,v in COMBINABLEDAMAGE_INDEX.items()}

PROCINDEX_INFO = {"Impact": {"name": "Impact", "duration": 6, "max_stacks": 5, "proc_index":0}, 
                  "Puncture": {"name": "Puncture","duration": 6,"max_stacks": 5, "proc_index":1},
                "Slash": {"name": "Slash","duration": 6,"max_stacks": 1, "damage_scaling":0.35, "proc_index":2}, 
                "Heat": {"name": "Heat","duration": 6,"max_stacks": 1,"refresh": True, "damage_scaling":0.5, "proc_index":3},
                "Cold": {"name": "Cold","duration": 6,"max_stacks": 9, "proc_index":4},
                "Electric": {"name": "Electric","duration": 6,"max_stacks": 1, "damage_scaling":0.5, "proc_index":5},
                "Toxin": {"name": "Toxin","duration": 6,"max_stacks": 1, "damage_scaling":0.5, "proc_index":6},
                "Blast": {"name": "Blast","duration": 10,"max_stacks": 4, "proc_index":7},
                "Radiation": {"name": "Radiation","duration": 12,"max_stacks": 10, "proc_index":8},
                "Gas": {"name": "Gas","duration": 6,"max_stacks": 10, "damage_scaling":0.5, "proc_index":9},
                "Magnetic": {"name": "Magnetic","duration": 6,"max_stacks": 10, "proc_index":10},
                "Viral": {"name": "Viral","duration": 6,"max_stacks": 10, "proc_index":11},
                "Corrosive": {"name": "Corrosive","duration": 8,"max_stacks": 10, "proc_index":12},
                "Void": {"name": "Void","duration": 3,"max_stacks": 1, "proc_index":13},
                "Knockdown": {"name": "Knockdown","duration": 3,"max_stacks": 1, "proc_index":14},
                "Microwave": {"name": "Microwave","duration": 3,"max_stacks": 1, "proc_index":15}}


DEFAULT_ENEMY_CONFIG = {
        "base_health": 100.0,
        "base_armor": 0.0,
        "base_shield": 0.0,
        "base_level": 1.0,
        "base_dr": 1.0,
        "health_vulnerability": 1,
        "shield_vulnerability": 1,
        "health_type": "Flesh",
        "armor_type": "None",
        "shield_type": ["None", 'test'],
        "damage_controller_type": "DC_NORMAL",
        "critical_controller_type": "CC_NORMAL",
        "faction": "Tenno",
        "base_overguard": 0,
        "is_eximus": False,
        "proc_info": {
            "PT_IMPACT": {
                "name": "Impact",
                "duration": 6,
                "max_stacks": 3
            },
            "PT_PUNCTURE": {
                "name": "Puncture",
                "duration": 6,
                "max_stacks": 3
            },
            "PT_SLASH": {
                "name": "Slash",
                "duration": 6,
                "max_stacks": 4,
                "damage_scaling":1
            },
            "PT_HEAT": {
                "name": "Heat",
                "duration": 6,
                "max_stacks": 4,
                "refresh": False,
                "damage_scaling":1
            },
            "PT_COLD": {
                "name": "Cold",
                "duration": 6,
                "max_stacks": 4
            },
            "PT_ELECTRIC": {
                "name": "Electric",
                "duration": 6,
                "max_stacks": 4,
                "damage_scaling":1
            },
            "PT_TOXIN": {
                "name": "Toxin",
                "duration": 6,
                "max_stacks": 4,
                "damage_scaling":1
            },
            "PT_BLAST": {
                "name": "Blast",
                "duration": 6,
                "max_stacks": 4
            },
            "PT_RADIATION": {
                "name": "Radiation",
                "duration": 12,
                "max_stacks": 4
            },
            "PT_GAS": {
                "name": "Gas",
                "duration": 6,
                "max_stacks": 4,
                "damage_scaling":1
            },
            "PT_MAGNETIC": {
                "name": "Magnetic",
                "duration": 6,
                "max_stacks": 4
            },
            "PT_VIRAL": {
                "name": "Viral",
                "duration": 6,
                "max_stacks": 0
            },
            "PT_CORROSIVE": {
                "name": "Corrosive",
                "duration": 8,
                "max_stacks": 4
            },
            "PT_RADIANT": {
                "name": "Void",
                "duration": 3,
                "max_stacks": 1
            }
        }
}
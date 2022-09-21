exec open( 'config/pool.py', 'r' ) in globals()

def GetDraftYear() :
    return PoolYear + Started - 1

def GetStatsYear() :
    return PoolYear + Started - 1

MinimumSalary = 775000

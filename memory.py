import gd
import asyncio
import time
import win32gui
import win32api
import win32con
import neat

class _GeometryDash:
        def __init__(self):
            self.mem = gd.memory.get_memory()
            self.clicked = False
            self.gd_window = win32gui.FindWindow(None, "Geometry Dash")

        def mouse_input(self, val): # [-1, 1] float
            lparam = win32api.MAKELONG(10, 10)
            if val > 0.0:
                if not self.clicked:
                    win32api.SendMessage(self.gd_window, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
                self.clicked = True
            else:
                if self.clicked:
                    win32api.SendMessage(self.gd_window, win32con.WM_LBUTTONUP, win32con.MK_LBUTTON, lparam)
                self.clicked = False
            return 1.0 if val > 0.0 else 0.0

_gd_game = _GeometryDash()
#exit()
X_SIZE = 20
Y_SIZE = 10
ROUND_SIZE = 10
EXTRA_SIZE = 9 # size, velocity, gravity, gamemode * 6
OBJ_SIZE = 31
TOTAL_SIZE = X_SIZE * Y_SIZE * OBJ_SIZE + EXTRA_SIZE
print(f"TOTAL_SIZE = {TOTAL_SIZE}")

"""
class GameModeConstant(int,  gd.utils.enums.Enum):
    CUBE =   0x000000000000
    SHIP =   0x000000000001
    UFO =    0x000000000100
    BALL =   0x000000010000
    WAVE =   0x000001000000
    ROBOT =  0x000100000000
    SPIDER = 0x010000000000
    

def get_gamemode(gd_mem):
    return GameModeConstant.from_value(gd_mem.read_int64(0x3222d0, 0x164, 0x224, 0x638) & ((1 << 48) - 1))

def set_gamemode(gd_mem, gamemode):
    return gd_mem.write_int64(GameModeConstant.from_value(gamemode).value | get_gravity(m) << 48, 0x3222d0, 0x164, 0x224, 0x638)
"""
def get_velocity(gd_mem):
    return gd_mem.read_float32(0x3222d0, 0x164, 0x224, 0x62c)

def set_velocity(gd_mem, velocity):
    return gd_mem.write_float32(velocity, 0x3222d0, 0x164, 0x224, 0x62c)

#def get_paused(gd_mem):
#    return gd_mem.read_bool(0x3222d0, 0x164, 0x224, 0x4720)

def get_gravity(gd_mem): # bool if gravity is inverted
    return gd_mem.read_bool(0x3222d0, 0x164, 0x224, 0x63e)

def set_gravity(gd_mem, gravity): # 0 = default, 1 = inverted
    gd_mem.write_bool(gravity, 0x3222d0, 0x164, 0x224, 0x63e)

def level_updates():
    m = gd.memory.get_memory()
    print("")
    old_velocity = 0.0
    old_size = -1
    old_gravity = -1
    while True:
        new_velocity = get_velocity(m)
        new_size = m.get_size()
        new_gravity = get_gravity(m)
        if new_velocity != old_velocity or new_size != old_size or new_gravity != old_gravity:
            print (f"\rVELOCITY = {new_velocity}, SIZE = {new_size}, GRAVITY = {new_gravity}" + " " * 0x50, end = "")
        old_velocity = new_velocity
        old_size = new_size
        old_gravity = new_gravity
        #time.sleep(0.01)

#m = gd.memory.get_memory()
#level_updates()
#exit()
gd_window = win32gui.FindWindow(None, "Geometry Dash")

def my_round(val):
    val = int(val)
    val -= val % ROUND_SIZE
    return val

async def init():
    global _mem, _level, _objects
    global _obj_id_convert
    _obj_id_convert = {}
    _objects = {}
    client = gd.Client()
    _mem = gd.memory.get_memory()
    _level = await client.get_level(20424353)
    print (_level.name)
    m = {}
    level = _level
    print (len((level.open_editor().get_objects())))
    for obj in level.open_editor().get_objects():
        if obj.id not in m:
            m[obj.id] = []
        m[obj.id].append((obj.x, obj.y + 100.0))
        obj_tpl = (my_round(obj.x), my_round(obj.y + 100.0))
        #print (obj_tpl)
        if obj_tpl not in _objects:
            _objects[obj_tpl] = []
        _objects[obj_tpl].append(obj.id)
        #print ("id = {}, x = {}, y = {}".format(obj.id, obj_tpl[0], obj_tpl[1]))
    for i, id in enumerate(m):
        #print ("{} = {}".format(id, len(m[id])))
        _obj_id_convert[id] = i
    print (len(m)) # 30
    assert len(m) == OBJ_SIZE - 1

def get_surroundings():
    mem = _mem
    objects = _objects
    obj_id_convert = _obj_id_convert
    inputs = [0.0] * TOTAL_SIZE
    t1 = time.time()
    start_x = my_round(mem.x_pos - 35)
    start_y = my_round(mem.y_pos - 50)
    #print (mem.x_pos)
    #print ((start_x, start_x + X_SIZE * ROUND_SIZE))
    #print (mem.y_pos)
    #print ((start_y, start_y + Y_SIZE * ROUND_SIZE))
    fix_x = lambda x : int((x - start_x) / ROUND_SIZE)
    fix_y = lambda x : int((y - start_y) / ROUND_SIZE)
    found_objs = 0
    for x in range(start_x, start_x + X_SIZE * ROUND_SIZE, ROUND_SIZE):
        for y in range(start_y, start_y + Y_SIZE * ROUND_SIZE, ROUND_SIZE):
            if y <= 95:
                at = fix_x(x) + fix_y(y) * X_SIZE + (OBJ_SIZE-1) * X_SIZE * Y_SIZE
                #print(f"at ={at}")
                inputs[at] = 1.0
                found_objs += 1
            if (x, y) not in objects:
                continue
            for obj_id in objects[(x, y)]:
                found_objs += 1
                #print("found obj - {}".format(obj_id))
                at = fix_x(x) + fix_y(y) * X_SIZE + obj_id_convert[obj_id] * X_SIZE * Y_SIZE
                #print(f"at = {at}")
                inputs[at] = 1.0
    inputs[TOTAL_SIZE-OBJ_SIZE+0] = mem.get_size()
    inputs[TOTAL_SIZE-OBJ_SIZE+1] = get_velocity(mem)
    inputs[TOTAL_SIZE-OBJ_SIZE+2] = -1 if get_gravity(mem) else 1
    gm_state = mem.get_gamemode_state()
    for i in range(6):
        inputs[TOTAL_SIZE-OBJ_SIZE+3+i] = 1 if gm_state[i] else -1

    t2 = time.time()
    #print ("time to get surroundings = {}".format(t2 - t1))
    return inputs, found_objs


AI_FPS = 90.0
min_fps = 5000.0
def eval_genomes(genomes, config):
    global min_fps
    gd_game = _gd_game
    mem = gd_game.mem
    #level = _level
    #objects = _objects
    print("starting..")
    for i, (genome_id, genome) in enumerate(genomes):
        while not mem.is_dead():
            pass
        while mem.is_dead():
            pass
        genome.fitness = 0.0
        net = neat.nn.FeedForwardNetwork.create(genome, config)
        print ("Genome {}/32, id = {}...".format(i+1, genome_id))
        count = 0
        prev_output = -1.0
        start_time = time.time()
        next_frame_time = time.time() + (1.0 / AI_FPS)
        while True:
            inputs, obj_count = get_surroundings()
            t1 = time.time()
            outputs = net.activate(inputs)
            t2 = time.time()
            #print ("time to activate = {}".format(t2 - t1))
            assert len(outputs) == 1
            #print (outputs[0])

            count += 1
            res = gd_game.mouse_input(outputs[0])
            if count % 5 == 0:
                if (abs(prev_output - outputs[0]) > 0.001):
                    print("")
                print(f"\rOutput {count} = {round(outputs[0], 4)}, objs_found = {obj_count}, res = {res}", end = "")
                prev_output = outputs[0]
            genome.fitness -= res * 23.0
            if mem.is_dead():
                print("")
                genome.fitness += (mem.x_pos / 3) ** 2
                genome.fitness /= 100.0
                print ("FITNESS = {}".format(genome.fitness))
                break
            t_ = time.time()
            if t_ > next_frame_time:
                print(f"\nTIME SLOWDOWN BY {round(t_ - next_frame_time, 5)}")
            else:
                time.sleep(next_frame_time - t_)
            next_frame_time = next_frame_time + (1.0 / AI_FPS)
            #time.sleep(0.01)
        gd_game.mouse_input(-1)
        curr_fps = float(count) / (time.time() - start_time)
        min_fps = min(curr_fps, min_fps)
        #print ("\nAverage fps - {}".format(round(curr_fps, 4)))
    print ("\nMIN FPS - {}".format(min_fps))

def main():
    asyncio.get_event_loop().run_until_complete(init())
    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction, neat.DefaultSpeciesSet, neat.DefaultStagnation, "./neat_config.txt")
    print("neat.population")
    p = neat.Population(config)

    p.add_reporter(neat.StdOutReporter(True))
    p.add_reporter(neat.StatisticsReporter())
    print("p.run...")
    p.run(eval_genomes)

    


if __name__ == "__main__":
    main()



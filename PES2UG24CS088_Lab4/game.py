import pygame
import random

TILE = 40
COLS, ROWS = 20, 15
WALL, FLOOR, CHEST, KEY = 0, 1, 2, 3
SPIKE, PIT = 4, 5
TRAP_MESSAGES = {
    SPIKE: "Spiked! Back to start!",
    PIT: "Fell in a pit! Back to start!",
}
SPEED = 3
GUARD_SPEED = 2

def generate_world():
    grid = [[WALL]*COLS for _ in range(ROWS)]
    rooms = []
    for _ in range(8):
        w = random.randint(3,6)
        h = random.randint(3,5)
        x = random.randint(1, COLS-w-1)
        y = random.randint(1, ROWS-h-1)
        room = pygame.Rect(x, y, w, h)
        overlap = any(room.inflate(2,2).colliderect(r) for r in rooms)
        if not overlap:
            rooms.append(room)
            for ry in range(y, y+h):
                for rx in range(x, x+w):
                    grid[ry][rx] = FLOOR

    corridor = set()
    for i in range(len(rooms)-1):
        ax, ay = rooms[i].centerx, rooms[i].centery
        bx, by = rooms[i+1].centerx, rooms[i+1].centery
        cx = ax
        while cx != bx:
            grid[ay][cx] = FLOOR
            corridor.add((cx, ay))
            cx += 1 if bx > cx else -1
        cy = ay
        while cy != by:
            grid[cy][bx] = FLOOR
            corridor.add((bx, cy))
            cy += 1 if by > cy else -1

    if len(rooms) < 2:
        return generate_world()
    cr, ck = rooms[-1], rooms[-2]
    grid[cr.centery][cr.centerx] = CHEST
    grid[ck.centery][ck.centerx] = KEY
    guard_row = cr.centery - 1
    guard_tiles = {(x, guard_row) for x in range(cr.left, cr.right)}
    place_traps(grid, rooms, corridor | guard_tiles)

    start = rooms[0] if rooms else None
    patrol = ((cr.left*TILE+6, guard_row*TILE+6), ((cr.right-1)*TILE+6, guard_row*TILE+6))
    return grid, start, patrol

def place_traps(grid, rooms, keep_clear):
    spots = [(x, y) for room in rooms[1:]
             for y in range(room.top, room.bottom)
             for x in range(room.left, room.right)
             if grid[y][x] == FLOOR and (x, y) not in keep_clear]
    for _ in range(50):
        traps = random.sample(spots, min(len(spots), random.randint(3, 6)))
        for x, y in traps:
            grid[y][x] = random.choice((SPIKE, PIT))
        if is_winnable(grid, rooms[0].x, rooms[0].y):
            return
        for x, y in traps:
            grid[y][x] = FLOOR

def is_winnable(grid, sx, sy):
    seen, stack, found = {(sx, sy)}, [(sx, sy)], set()
    while stack:
        x, y = stack.pop()
        found.add(grid[y][x])
        for nx, ny in ((x+1,y), (x-1,y), (x,y+1), (x,y-1)):
            if (nx, ny) not in seen and grid[ny][nx] in (FLOOR, KEY, CHEST):
                seen.add((nx, ny))
                stack.append((nx, ny))
    return KEY in found and CHEST in found

COLORS = {
    WALL: (60,50,70),
    FLOOR: (200,190,170),
    CHEST: (200,160,30),
    KEY: (220,220,60),
    SPIKE: (190,60,60),
    PIT: (20,15,10),
}

MINI = 6  # mini-map pixels per tile
MINI_COLORS = {
    FLOOR: (130,125,115),
    KEY: (255,240,0),
    CHEST: (255,110,0),
}

class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 28, 28)
        self.color = (60,120,220)
        self.has_key = False

    def move(self, keys, grid, rows, cols):
        dx=dy=0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx=-SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx=SPEED
        if keys[pygame.K_UP] or keys[pygame.K_w]: dy=-SPEED
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy=SPEED
        self._try_move(dx,0,grid,rows,cols)
        self._try_move(0,dy,grid,rows,cols)

    def _try_move(self, dx, dy, grid, rows, cols):
        new = self.rect.move(dx,dy)
        for px,py in [(new.left,new.top),(new.right-1,new.top),(new.left,new.bottom-1),(new.right-1,new.bottom-1)]:
            c,r=px//TILE,py//TILE
            if not(0<=r<rows and 0<=c<cols) or grid[r][c]==WALL:
                return
        self.rect=new

    def draw(self, screen):
        pygame.draw.ellipse(screen, self.color, self.rect)
        if self.has_key:
            pygame.draw.circle(screen, (220,220,60), (self.rect.right-6, self.rect.top+6), 5)

class Guard:
    def __init__(self, a, b):
        self.rect = pygame.Rect(a[0], a[1], 28, 28)
        self.a, self.b = a, b
        self.target = b
        self.color = (40,180,90)

    def update(self):
        tx, ty = self.target
        dx = max(-GUARD_SPEED, min(GUARD_SPEED, tx - self.rect.x))
        dy = max(-GUARD_SPEED, min(GUARD_SPEED, ty - self.rect.y))
        self.rect.move_ip(dx, dy)
        if self.rect.topleft == self.target:
            self.target = self.a if self.target == self.b else self.b

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect, border_radius=6)


WIDTH = COLS * TILE
HEIGHT = ROWS * TILE + 50
FPS = 60

class GameEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Treasure Hunt")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 24)
        self.big_font = pygame.font.SysFont("monospace", 40, bold=True)
        self.small_font = pygame.font.SysFont("monospace", 14, bold=True)
        self.reset()

    def reset(self):
        self.grid, start, patrol = generate_world()
        if start:
            sx = start.x * TILE + 6
            sy = start.y * TILE + 6
        else:
            sx, sy = TILE+6, TILE+6
        self.start_pos = (sx, sy)
        self.player = Player(sx, sy)
        self.guard = Guard(*patrol)
        self.won = False
        self.status = "Find the KEY, then the CHEST!"

    def send_to_start(self, message):
        self.player.rect.topleft = self.start_pos
        self.status = message

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r: self.reset()
        return True

    def update(self):
        if self.won: return
        keys = pygame.key.get_pressed()
        self.player.move(keys, self.grid, ROWS, COLS)
        pr = self.player.rect.centery // TILE
        pc = self.player.rect.centerx // TILE
        if 0<=pr<ROWS and 0<=pc<COLS:
            cell = self.grid[pr][pc]
            if cell == KEY:
                self.player.has_key = True
                self.grid[pr][pc] = FLOOR
                self.status = "Got the key! Find the CHEST!"
            elif cell == CHEST:
                if self.player.has_key:
                    self.won = True
                    self.status = "Treasure found!"
                else:
                    self.status = "You need the KEY first!"
            elif cell in TRAP_MESSAGES:
                self.send_to_start(TRAP_MESSAGES[cell])
        self.guard.update()
        if self.player.rect.colliderect(self.guard.rect):
            self.send_to_start("Caught by the guard! Back to start!")

    def draw(self):
        self.screen.fill((30,25,40))
        for r in range(ROWS):
            for c in range(COLS):
                cell = self.grid[r][c]
                rect = pygame.Rect(c*TILE, r*TILE, TILE, TILE)
                pygame.draw.rect(self.screen, COLORS[cell], rect)
                if cell == KEY:
                    pygame.draw.circle(self.screen, (255,240,60),(c*TILE+TILE//2, r*TILE+TILE//2),10)
                elif cell == CHEST:
                    pygame.draw.rect(self.screen,(180,120,20),rect.inflate(-12,-12),border_radius=4)
        self.guard.draw(self.screen)
        self.player.draw(self.screen)
        self.draw_minimap()
        hud = pygame.Rect(0,ROWS*TILE,WIDTH,50)
        pygame.draw.rect(self.screen,(20,20,35),hud)
        st = self.font.render(self.status+"  |  R=Restart", True, (200,200,200))
        self.screen.blit(st,(8,ROWS*TILE+13))
        self.draw_inventory()
        if self.won:
            ov=pygame.Surface((WIDTH,ROWS*TILE),pygame.SRCALPHA)
            ov.fill((0,0,0,140))
            self.screen.blit(ov,(0,0))
            msg=self.big_font.render("TREASURE FOUND!", True,(220,180,30))
            sub=self.font.render("Press R to Play Again",True,(180,180,180))
            self.screen.blit(msg,(WIDTH//2-msg.get_width()//2,ROWS*TILE//2-30))
            self.screen.blit(sub,(WIDTH//2-sub.get_width()//2,ROWS*TILE//2+20))
        pygame.display.flip()

    def draw_inventory(self):
        slot = pygame.Rect(WIDTH-46, ROWS*TILE+7, 36, 36)
        label = self.small_font.render("INV", True, (160,160,160))
        self.screen.blit(label, (slot.x - label.get_width() - 6, slot.centery - label.get_height()//2))
        pygame.draw.rect(self.screen, (45,45,65), slot, border_radius=4)
        pygame.draw.rect(self.screen, (200,200,200), slot, 2, border_radius=4)
        if self.player.has_key:
            color = (255,240,60)
            cy = slot.centery
            pygame.draw.circle(self.screen, color, (slot.x+11, cy), 6, 3)
            pygame.draw.line(self.screen, color, (slot.x+16, cy), (slot.right-6, cy), 3)
            pygame.draw.line(self.screen, color, (slot.right-8, cy), (slot.right-8, cy+6), 3)
            pygame.draw.line(self.screen, color, (slot.right-13, cy), (slot.right-13, cy+5), 3)

    def draw_minimap(self):
        mini = pygame.Surface((COLS*MINI, ROWS*MINI), pygame.SRCALPHA)
        mini.fill((0,0,0,170))
        for r in range(ROWS):
            for c in range(COLS):
                cell = self.grid[r][c]
                if cell != WALL:
                    color = MINI_COLORS.get(cell, MINI_COLORS[FLOOR])
                    mini.fill(color, (c*MINI, r*MINI, MINI, MINI))
        pc = self.player.rect.centerx // TILE
        pr = self.player.rect.centery // TILE
        mini.fill((255,255,255), (pc*MINI, pr*MINI, MINI, MINI))
        x, y = WIDTH - mini.get_width() - 10, 10
        self.screen.blit(mini, (x, y))
        pygame.draw.rect(self.screen, (230,230,230), (x-1, y-1, mini.get_width()+2, mini.get_height()+2), 1)

    def run(self):
        running=True
        while running:
            running=self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()

if __name__ == "__main__":
    engine = GameEngine()
    engine.run()

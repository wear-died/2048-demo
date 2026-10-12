import pygame
import sys
import random

# 颜色定义
BLACK = (0, 0, 10)
RED = (200, 50, 50)
GRAY = (200, 200, 200)
LIGHT_GRAY = (180, 180, 180)
BEIGE = (245, 222, 179)
DARK_BEIGE = (220, 200, 160)
BUTTON_COLOR = (70, 130, 180)
BUTTON_HOVER = (100, 160, 210)
GAME_OVER_COLOR = (200, 50, 50)
TEXT_COLOR = RED

# 窗口布局
WINDOW_WIDTH = 300
TOP_HEIGHT = 60
WINDOW_HEIGHT = TOP_HEIGHT + 300
BOARD_SIZE = 300
FONT_SIZE = 24


def move_left(grid):
    size = len(grid)
    new_grid = [row[:] for row in grid]
    moved = False
    gain = 0
    merge_count = 0
    animations = []  # (src_r, src_c, dst_r, dst_c, val)

    for r in range(size):
        row = grid[r]
        # 收集非零单元格 (列, 值)
        cells = [(c, row[c]) for c in range(size) if row[c] != 0]
        merged = []
        sources = []  # 每个目标列对应的源列列表（可能多个）
        i = 0
        while i < len(cells):
            c1, val1 = cells[i]
            if i + 1 < len(cells) and cells[i+1][1] == val1:
                new_val = val1 * 2
                if new_val > 65536:
                    merged.append(val1)
                    sources.append([c1])
                    i += 1
                else:
                    merged.append(new_val)
                    sources.append([c1, cells[i+1][0]])
                    gain += val1
                    merge_count += 1
                    i += 2
            else:
                merged.append(val1)
                sources.append([c1])
                i += 1
        # 补0
        while len(merged) < size:
            merged.append(0)
            sources.append([])

        # 更新new_grid并生成动画条目
        for dst_c in range(size):
            val = merged[dst_c]
            if val != 0:
                new_grid[r][dst_c] = val
                src_cols = sources[dst_c]
                for src_c in src_cols:
                    # 只有移动或合成时才添加动画
                    if src_c != dst_c or len(src_cols) > 1:
                        # 记录原始值（即grid[r][src_c]）
                        animations.append((r, src_c, r, dst_c, grid[r][src_c]))
                        moved = True
            else:
                new_grid[r][dst_c] = 0

    return new_grid, moved, gain, merge_count, animations


def move_right(grid):
    size = len(grid)
    new_grid = [row[:] for row in grid]
    moved = False
    gain = 0
    merge_count = 0
    animations = []

    for r in range(size):
        row = grid[r]
        cells = [(c, row[c]) for c in range(size) if row[c] != 0]
        # 从右向左处理
        cells_rev = list(reversed(cells))
        merged = []
        sources = []
        i = 0
        while i < len(cells_rev):
            c1, val1 = cells_rev[i]
            if i + 1 < len(cells_rev) and cells_rev[i+1][1] == val1:
                new_val = val1 * 2
                if new_val > 65536:
                    merged.append(val1)
                    sources.append([c1])
                    i += 1
                else:
                    merged.append(new_val)
                    sources.append([c1, cells_rev[i+1][0]])
                    gain += val1
                    merge_count += 1
                    i += 2
            else:
                merged.append(val1)
                sources.append([c1])
                i += 1
        while len(merged) < size:
            merged.append(0)
            sources.append([])
        # 反转回正常顺序
        merged.reverse()
        sources.reverse()

        for dst_c in range(size):
            val = merged[dst_c]
            if val != 0:
                new_grid[r][dst_c] = val
                src_cols = sources[dst_c]
                for src_c in src_cols:
                    if src_c != dst_c or len(src_cols) > 1:
                        animations.append((r, src_c, r, dst_c, grid[r][src_c]))
                        moved = True
            else:
                new_grid[r][dst_c] = 0

    return new_grid, moved, gain, merge_count, animations


def move_up(grid):
    size = len(grid)
    trans = [[grid[r][c] for r in range(size)] for c in range(size)]
    new_trans, moved, gain, merge_count, trajs = move_left(trans)
    new_grid = [[new_trans[c][r] for c in range(size)] for r in range(size)]
    adjusted = []
    for fr, fc, tr, tc, val in trajs:
        adjusted.append((fc, fr, tc, tr, val))
    return new_grid, moved, gain, merge_count, adjusted


def move_down(grid):
    size = len(grid)
    trans = [[grid[r][c] for r in range(size)] for c in range(size)]
    new_trans, moved, gain, merge_count, trajs = move_right(trans)
    new_grid = [[new_trans[c][r] for c in range(size)] for r in range(size)]
    adjusted = []
    for fr, fc, tr, tc, val in trajs:
        adjusted.append((fc, fr, tc, tr, val))
    return new_grid, moved, gain, merge_count, adjusted


class Game:
    def __init__(self, size, speed):
        self.size = size
        self.grid_size = size
        self.speed = speed
        self.duration_ms = 1100 - 100 * speed  # 1~10 -> 1000~100 ms
        self.grid = [[0] * size for _ in range(size)]
        self.old_grid = None   # 用于动画期间绘制未移动的块
        self.score = 0
        self.auto_mode = False
        self.state = 'IDLE'   # IDLE, MOVING, GAMEOVER
        self.animations = []  # 当前动画帧数据
        self.animation_progress = 0.0
        self.animation_start_time = 0
        self.game_over = False
        self.add_random_block()
        self.add_random_block()

    def evaluate(self, grid):
        """评估一个棋盘状态的好坏，分数越高越好"""
        size = self.grid_size
        empty_count = sum(1 for r in range(size) for c in range(size) if grid[r][c] == 0)
        
        # 1. 空位奖励（非常重要）
        score = empty_count * 100
        
        # 2. 最大块是否在角落（强制锁角）
        max_val = max(max(row) for row in grid)
        corners = [(0,0), (0,size-1), (size-1,0), (size-1,size-1)]
        for r, c in corners:
            if grid[r][c] == max_val:
                score += 1000
                break
        
        # 3. 单调性（蛇形方向：按行从左到右，下一行从右到左）
        mono_score = 0
        for r in range(size):
            row = grid[r]
            if r % 2 == 0:
                # 从左到右 递增
                for c in range(size-1):
                    if row[c] <= row[c+1] and row[c] != 0:
                        mono_score += 1
            else:
                # 从右到左 递增
                for c in range(size-1):
                    if row[c] >= row[c+1] and row[c] != 0:
                        mono_score += 1
        score += mono_score * 50
        
        # 4. 惩罚相邻块差异过大（平滑度）
        penalty = 0
        for r in range(size):
            for c in range(size):
                if grid[r][c] == 0:
                    continue
                # 右邻
                if c + 1 < size and grid[r][c+1] != 0:
                    penalty += abs(grid[r][c] - grid[r][c+1])
                # 下邻
                if r + 1 < size and grid[r+1][c] != 0:
                    penalty += abs(grid[r][c] - grid[r+1][c])
        score -= penalty * 10
        
        return score


    def add_random_block(self):
        empties = [(r, c) for r in range(self.grid_size) for c in range(self.grid_size) if self.grid[r][c] == 0]
        if empties:
            r, c = random.choice(empties)
            self.grid[r][c] = 2 if random.random() < 0.9 else 4

    def move(self, direction):
        if self.state != 'IDLE':
            return False
        if direction == 'left':
            new_grid, moved, gain, mc, trajs = move_left(self.grid)
        elif direction == 'right':
            new_grid, moved, gain, mc, trajs = move_right(self.grid)
        elif direction == 'up':
            new_grid, moved, gain, mc, trajs = move_up(self.grid)
        elif direction == 'down':
            new_grid, moved, gain, mc, trajs = move_down(self.grid)
        else:
            return False

        if moved:
            self.old_grid = [row[:] for row in self.grid]  # 保存移动前状态
            self.grid = new_grid
            self.score += gain
            self.animations = trajs
            self.state = 'MOVING'
            self.animation_progress = 0.0
            self.animation_start_time = pygame.time.get_ticks()
            return True
        return False

    def update_animation(self):
        if self.state != 'MOVING':
            return True
        now = pygame.time.get_ticks()
        elapsed = now - self.animation_start_time
        progress = elapsed / self.duration_ms
        if progress >= 1.0:
            self.animation_progress = 1.0
            self.finish_animation()
            return True
        else:
            self.animation_progress = progress
            return False

    def finish_animation(self):
        # 动画结束，生成新块，检查游戏结束
        self.add_random_block()
        self.state = 'IDLE'
        self.animations = []
        self.old_grid = None
        if self.is_game_over():
            self.state = 'GAMEOVER'

    def is_game_over(self):
        if any(0 in row for row in self.grid):
            return False
        for direction in ['up', 'down', 'left', 'right']:
            if direction == 'left':
                _, moved, _, _, _ = move_left(self.grid)
            elif direction == 'right':
                _, moved, _, _, _ = move_right(self.grid)
            elif direction == 'up':
                _, moved, _, _, _ = move_up(self.grid)
            elif direction == 'down':
                _, moved, _, _, _ = move_down(self.grid)
            if moved:
                return False
        return True

    def reset(self):
        self.grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        self.score = 0
        self.auto_mode = False
        self.state = 'IDLE'
        self.animations = []
        self.old_grid = None
        self.animation_progress = 0.0
        self.add_random_block()
        self.add_random_block()

    def auto_choose_direction(self):
        """重写：选择评估分数最高的方向"""
        dirs = ['up', 'down', 'left', 'right']
        best_dir = None
        best_score = -float('inf')
        
        # 为了模拟，需要深拷贝网格，且移动函数需要返回新网格
        # 我们复用已有的 move_left/right/up/down，它们返回 (new_grid, moved, ...)
        for d in dirs:
            # 复制当前网格
            import copy
            temp_grid = copy.deepcopy(self.grid)
            
            if d == 'left':
                new_grid, moved, _, _, _ = move_left(temp_grid)
            elif d == 'right':
                new_grid, moved, _, _, _ = move_right(temp_grid)
            elif d == 'up':
                new_grid, moved, _, _, _ = move_up(temp_grid)
            elif d == 'down':
                new_grid, moved, _, _, _ = move_down(temp_grid)
            
            if not moved:
                continue  # 无效移动直接跳过
            
            score = self.evaluate(new_grid)
            if score > best_score:
                best_score = score
                best_dir = d
        
        # 如果所有方向都无效（理论上游戏结束），返回 None
        return best_dir


def draw_block(screen, r, c, val, board_top, board_left, cell_size):
    margin = 4
    x = board_left + c * cell_size + margin
    y = board_top + r * cell_size + margin
    w = cell_size - 2 * margin
    pygame.draw.rect(screen, BEIGE, (x, y, w, w))
    pygame.draw.rect(screen, DARK_BEIGE, (x, y, w, w), 1)
    font = pygame.font.SysFont("arial", int(w * 0.6))
    text = font.render(str(val), True, RED)
    text_rect = text.get_rect(center=(x + w // 2, y + w // 2))
    screen.blit(text, text_rect)


def draw_block_at(screen, r, c, val, board_top, board_left, cell_size):
    margin = 4
    x = board_left + c * cell_size + margin
    y = board_top + r * cell_size + margin
    w = cell_size - 2 * margin
    x = int(round(x))
    y = int(round(y))
    pygame.draw.rect(screen, BEIGE, (x, y, w, w))
    pygame.draw.rect(screen, DARK_BEIGE, (x, y, w, w), 1)
    font = pygame.font.SysFont("arial", int(w * 0.6))
    text = font.render(str(val), True, RED)
    text_rect = text.get_rect(center=(x + w // 2, y + w // 2))
    screen.blit(text, text_rect)


def main():
    print("请输入规格和速度（两个数字，空格分隔）：")
    print("规格: 1-小(3x3), 2-中(4x4), 3-大(5x5)")
    print("速度: 1~10（对应完成一次移动的时间从1秒到0.1秒）")
    while True:
        try:
            spec, speed = map(int, input().split())
            if spec in (1, 2, 3) and 1 <= speed <= 10:
                break
            else:
                print("输入无效，请重新输入")
        except:
            print("输入格式错误，请重新输入")
    size = {1: 3, 2: 4, 3: 5}[spec]

    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("2048")
    clock = pygame.time.Clock()

    game = Game(size, speed)

    font = pygame.font.SysFont("arial", FONT_SIZE)
    small_font = pygame.font.SysFont("arial", 18)

    btn_rect = pygame.Rect(WINDOW_WIDTH - 70, 10, 60, 30)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if game.state == 'GAMEOVER':
                    continue
                if event.key == pygame.K_SPACE:
                    game.auto_mode = not game.auto_mode
                elif not game.auto_mode and game.state == 'IDLE':
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        game.move('up')
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        game.move('down')
                    elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        game.move('left')
                    elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                        game.move('right')
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and btn_rect.collidepoint(event.pos):
                    game.reset()

        # 自动模式
        if game.state == 'IDLE' and game.auto_mode:
            direction = game.auto_choose_direction()
            if direction is not None:
                game.move(direction)
            else:
                if game.is_game_over():
                    game.state = 'GAMEOVER'

        # 更新动画
        if game.state == 'MOVING':
            game.update_animation()

        # 绘制
        screen.fill(BLACK)

        # 顶部栏
        speed_text = font.render(f"sp: {game.speed}", True, RED)
        screen.blit(speed_text, (10, 10))
        score_text = font.render(f"sc: {game.score}", True, RED)
        score_rect = score_text.get_rect(center=(WINDOW_WIDTH // 2, 10 + 15))
        screen.blit(score_text, score_rect)
        mouse_pos = pygame.mouse.get_pos()
        if btn_rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, BUTTON_HOVER, btn_rect)
        else:
            pygame.draw.rect(screen, BUTTON_COLOR, btn_rect)
        reset_text = small_font.render("re", True, RED)
        text_rect = reset_text.get_rect(center=btn_rect.center)
        screen.blit(reset_text, text_rect)

        # 游戏板
        board_top = TOP_HEIGHT
        board_left = 0
        cell_size = BOARD_SIZE // game.grid_size

        # 绘制网格背景
        for r in range(game.grid_size):
            for c in range(game.grid_size):
                rect = pygame.Rect(board_left + c * cell_size, board_top + r * cell_size, cell_size, cell_size)
                pygame.draw.rect(screen, BLACK, rect)
                pygame.draw.rect(screen, LIGHT_GRAY, rect, 1)

        if game.state == 'IDLE' or game.state == 'GAMEOVER':
            # 直接绘制网格
            for r in range(game.grid_size):
                for c in range(game.grid_size):
                    val = game.grid[r][c]
                    if val != 0:
                        draw_block(screen, r, c, val, board_top, board_left, cell_size)
        elif game.state == 'MOVING':
            # 使用old_grid绘制未移动的块
            anim_sources = set()
            for (fr, fc, tr, tc, val) in game.animations:
                anim_sources.add((fr, fc))
            # 绘制old_grid中不在动画源中的块
            for r in range(game.grid_size):
                for c in range(game.grid_size):
                    val = game.old_grid[r][c]
                    if val != 0 and (r, c) not in anim_sources:
                        draw_block(screen, r, c, val, board_top, board_left, cell_size)
            # 绘制动画块
            for (fr, fc, tr, tc, val) in game.animations:
                cur_r = fr + (tr - fr) * game.animation_progress
                cur_c = fc + (tc - fc) * game.animation_progress
                draw_block_at(screen, cur_r, cur_c, val, board_top, board_left, cell_size)

        # 游戏结束文字
        if game.state == 'GAMEOVER':
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 128))
            screen.blit(overlay, (0, 0))
            gameover_font = pygame.font.SysFont("arial", 48)
            go_text = gameover_font.render("GAME OVER", True, GAME_OVER_COLOR)
            go_rect = go_text.get_rect(center=(WINDOW_WIDTH // 2, TOP_HEIGHT + BOARD_SIZE // 2))
            screen.blit(go_text, go_rect)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
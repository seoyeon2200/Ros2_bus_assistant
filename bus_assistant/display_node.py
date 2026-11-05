"""
Display Node — /display_text 구독 → tkinter GUI 표시
             — 버스 색깔 버튼 클릭 → /bus_color 발행 → 자율주행 시작
"""

import queue
import threading
import tkinter as tk
import tkinter.font as tkfont
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


BG_COLOR   = '#1a1a2e'
TEXT_COLOR = '#e0e0e0'
ACCENT     = '#00d4ff'
WIN_W, WIN_H = 600, 440

_BUS_BUTTONS = [
    ('빨간 버스',  'red',    '#cc2222', '#ff6666'),
    ('파란 버스',  'blue',   '#1144cc', '#4488ff'),
    ('초록 버스',  'green',  '#117711', '#44cc44'),
    ('노란 버스',  'yellow', '#bb8800', '#ffcc00'),
]

_KOREAN_FONT_CANDIDATES = [
    'NanumGothic', 'Nanum Gothic', 'NanumBarunGothic',
    'Noto Sans CJK KR', 'Noto Sans KR', 'UnDotum',
    'Baekmuk Gulim', 'DejaVu Sans',
]


def _find_korean_font(root: tk.Tk) -> str:
    available = set(tkfont.families(root))
    for name in _KOREAN_FONT_CANDIDATES:
        if name in available:
            return name
    return 'TkDefaultFont'


class DisplayNode(Node):
    def __init__(self, gui_queue: queue.Queue):
        super().__init__('display_node')
        self._queue = gui_queue
        self._pub_bus_color = self.create_publisher(String, '/selected_bus', 10)
        self.create_subscription(String, '/display_text', self._text_cb, 10)
        self.create_subscription(String, '/robot_state', self._state_cb, 10)
        self.get_logger().info('DisplayNode 시작')

    def _text_cb(self, msg: String):
        self._queue.put(('text', msg.data))

    def _state_cb(self, msg: String):
        self._queue.put(('state', msg.data))

    def publish_bus_color(self, color: str):
        msg = String()
        msg.data = color
        self._pub_bus_color.publish(msg)
        self.get_logger().info(f'버스 선택: {color}')


class DisplayGUI:
    _STATE_MAP = {
        'idle':       ('대기 중',   '#888888'),
        'navigating': ('이동 중',   '#00d4ff'),
        'arrived':    ('도착 완료', '#00ff88'),
    }

    def __init__(self, gui_queue: queue.Queue, node: DisplayNode):
        self._queue = gui_queue
        self._node  = node
        self._root  = tk.Tk()
        self._root.title('버스 안내 로봇')
        self._root.configure(bg=BG_COLOR)
        self._root.geometry(f'{WIN_W}x{WIN_H}')
        self._root.resizable(False, False)

        font_name = _find_korean_font(self._root)

        # 상단 강조 바
        tk.Frame(self._root, bg=ACCENT, height=6).pack(fill='x')

        # 타이틀
        tk.Label(
            self._root, text='승하차 안내 로봇',
            bg=BG_COLOR, fg=ACCENT,
            font=(font_name, 16, 'bold'),
        ).pack(pady=(12, 0))

        # 구분선
        tk.Frame(self._root, bg='#333355', height=1).pack(fill='x', padx=20, pady=6)

        # 메인 안내 문구
        self._text_var = tk.StringVar(value='안내 로봇 준비 완료\n목적지 버스를 선택해 주세요')
        tk.Label(
            self._root,
            textvariable=self._text_var,
            bg=BG_COLOR, fg=TEXT_COLOR,
            font=(font_name, 22, 'bold'),
            wraplength=560,
            justify='center',
        ).pack(expand=True)

        # 버스 선택 버튼
        tk.Label(
            self._root, text='탑승할 버스 선택',
            bg=BG_COLOR, fg='#aaaaaa',
            font=(font_name, 11),
        ).pack(pady=(4, 2))

        btn_frame = tk.Frame(self._root, bg=BG_COLOR)
        btn_frame.pack(pady=(0, 10))

        self._buttons = {}
        for label, color_key, bg, hover in _BUS_BUTTONS:
            btn = tk.Button(
                btn_frame,
                text=label,
                bg=bg, fg='white',
                activebackground=hover,
                activeforeground='white',
                font=(font_name, 13, 'bold'),
                width=8, height=2,
                relief='flat', bd=0, cursor='hand2',
                command=lambda c=color_key: self._on_bus_select(c),
            )
            btn.pack(side='left', padx=6)
            self._buttons[color_key] = btn

        # 하단 상태 표시
        bottom = tk.Frame(self._root, bg='#0d0d1e')
        bottom.pack(fill='x', side='bottom')

        self._state_var   = tk.StringVar(value='상태: 대기 중')
        self._state_label = tk.Label(
            bottom,
            textvariable=self._state_var,
            bg='#0d0d1e', fg='#888888',
            font=(font_name, 13),
        )
        self._state_label.pack(pady=6)

        self._poll()

    def _on_bus_select(self, color: str):
        self._node.publish_bus_color(color)
        # 선택한 버튼 강조, 나머지 흐리게
        for key, btn in self._buttons.items():
            original_bg = dict(_BUS_BUTTONS)[key] if False else [
                bg for lbl, k, bg, _ in _BUS_BUTTONS if k == key][0]
            if key == color:
                btn.config(relief='solid', bd=2)
            else:
                btn.config(relief='flat', bd=0)

    def _poll(self):
        try:
            while True:
                kind, value = self._queue.get_nowait()
                if kind == 'text':
                    self._text_var.set(value)
                elif kind == 'state':
                    label, color = self._STATE_MAP.get(value, ('알 수 없음', '#888888'))
                    self._state_var.set(f'상태: {label}')
                    self._state_label.config(fg=color)
                    if value == 'idle':
                        for btn in self._buttons.values():
                            btn.config(relief='flat', bd=0)
        except queue.Empty:
            pass
        self._root.after(100, self._poll)

    def run(self):
        self._root.mainloop()


def main(args=None):
    gui_q = queue.Queue()

    rclpy.init(args=args)
    node = DisplayNode(gui_q)

    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    gui = DisplayGUI(gui_q, node)
    try:
        gui.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

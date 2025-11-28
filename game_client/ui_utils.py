"""
UI Utilities for Polish & User Feedback

Provides reusable components for:
- Loading indicators
- Error popups
- Success notifications
- Confirmation dialogs
"""
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.animation import Animation
from kivy.clock import Clock


class LoadingIndicator:
    """Shows a loading popup with message"""
    
    def __init__(self):
        self.popup = None
    
    def show(self, message="Loading..."):
        """Display loading indicator"""
        if self.popup:
            self.popup.dismiss()
        
        content = BoxLayout(orientation='vertical', padding='20dp', spacing='10dp')
        
        # Message
        label = Label(text=message, font_size='18sp')
        content.add_widget(label)
        
        # Progress bar (indeterminate)
        progress = ProgressBar(max=100)
        content.add_widget(progress)
        
        # Animate progress bar
        def animate_progress(dt):
            if progress.value >= 100:
                progress.value = 0
            progress.value += 10
        
        Clock.schedule_interval(animate_progress, 0.1)
        
        self.popup = Popup(
            title='Please Wait',
            content=content,
            size_hint=(0.5, 0.3),
            auto_dismiss=False
        )
        self.popup.open()
    
    def dismiss(self):
        """Hide loading indicator"""
        if self.popup:
            Clock.unschedule(lambda dt: None)  # Stop animations
            self.popup.dismiss()
            self.popup = None


def show_error(title, message, callback=None):
    """
    Show user-friendly error popup
    
    Args:
        title: Error title
        message: Error description
        callback: Optional function to call when dismissed
    """
    content = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')
    
    # Error icon + message
    error_label = Label(
        text=f"❌ {message}",
        font_size='16sp',
        color=(1, 0.3, 0.3, 1),
        halign='center',
        valign='middle'
    )
    error_label.bind(size=error_label.setter('text_size'))
    content.add_widget(error_label)
    
    # OK button
    btn = Button(text='OK', size_hint_y=0.3, height='44dp')
    content.add_widget(btn)
    
    popup = Popup(
        title=title,
        content=content,
        size_hint=(0.6, 0.4)
    )
    
    def on_dismiss(*args):
        popup.dismiss()
        if callback:
            callback()
    
    btn.bind(on_release=on_dismiss)
    popup.open()
    
    return popup


def show_success(message, duration=2.0):
    """
    Show success notification that auto-dismisses
    
    Args:
        message: Success message
        duration: Seconds to display (default 2.0)
    """
    content = Label(
        text=f"✓ {message}",
        font_size='18sp',
        color=(0.3, 1, 0.3, 1),
        bold=True
    )
    
    popup = Popup(
        title='Success',
        content=content,
        size_hint=(0.5, 0.25),
        auto_dismiss=True
    )
    popup.open()
    
    # Auto-dismiss after duration
    Clock.schedule_once(lambda dt: popup.dismiss(), duration)
    
    return popup


def show_confirmation(title, message, on_yes, on_no=None):
    """
    Show confirmation dialog with Yes/No buttons
    
    Args:
        title: Dialog title
        message: Confirmation message
        on_yes: Function to call if Yes clicked
        on_no: Optional function to call if No clicked
    """
    content = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')
    
    # Message
    msg_label = Label(
        text=message,
        font_size='16sp',
        halign='center',
        valign='middle'
    )
    msg_label.bind(size=msg_label.setter('text_size'))
    content.add_widget(msg_label)
    
    # Buttons
    button_box = BoxLayout(orientation='horizontal', size_hint_y=0.3, spacing='10dp')
    
    yes_btn = Button(text='Yes', background_color=(0.3, 1, 0.3, 1))
    no_btn = Button(text='No', background_color=(1, 0.3, 0.3, 1))
    
    button_box.add_widget(no_btn)
    button_box.add_widget(yes_btn)
    content.add_widget(button_box)
    
    popup = Popup(
        title=title,
        content=content,
        size_hint=(0.6, 0.35),
        auto_dismiss=False
    )
    
    def on_yes_click(*args):
        popup.dismiss()
        if on_yes:
            on_yes()
    
    def on_no_click(*args):
        popup.dismiss()
        if on_no:
            on_no()
    
    yes_btn.bind(on_release=on_yes_click)
    no_btn.bind(on_release=on_no_click)
    
    popup.open()
    return popup


def show_info(title, message):
    """
    Show informational popup
    
    Args:
        title: Info title
        message: Info message
    """
    content = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')
    
    # Message
    info_label = Label(
        text=message,
        font_size='16sp',
        halign='center',
        valign='middle'
    )
    info_label.bind(size=info_label.setter('text_size'))
    content.add_widget(info_label)
    
    # OK button
    btn = Button(text='OK', size_hint_y=0.3, height='44dp')
    content.add_widget(btn)
    
    popup = Popup(
        title=title,
        content=content,
        size_hint=(0.5, 0.3)
    )
    
    btn.bind(on_release=popup.dismiss)
    popup.open()
    
    return popup


# Global loading indicator instance
_global_loading = LoadingIndicator()


def show_loading(message="Loading..."):
    """Show global loading indicator"""
    _global_loading.show(message)


def hide_loading():
    """Hide global loading indicator"""
    _global_loading.dismiss()

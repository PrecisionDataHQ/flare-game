package io.precisiondata.joyorbit.flare;

public final class JoyOrbitFlareActivity extends io.precisiondata.joyorbit.flare.sdl.SDLActivity {
    private boolean startDown, selectDown;
    @Override protected String[] getLibraries() {
        return new String[] {"joyorbit_flare_sdl2", "joyorbit_flare_image", "joyorbit_flare_mixer", "joyorbit_flare_ttf", "joyorbit_flare_main"};
    }
    @Override public void onWindowFocusChanged(boolean focused) {
        if (!focused) { startDown = false; selectDown = false; }
        super.onWindowFocusChanged(focused);
    }
    @Override public boolean dispatchKeyEvent(android.view.KeyEvent event) {
        if (event.getKeyCode() == android.view.KeyEvent.KEYCODE_BUTTON_START)
            startDown = event.getAction() == android.view.KeyEvent.ACTION_DOWN;
        if (event.getKeyCode() == android.view.KeyEvent.KEYCODE_BUTTON_SELECT)
            selectDown = event.getAction() == android.view.KeyEvent.ACTION_DOWN;
        if ((startDown && selectDown && event.getAction() == android.view.KeyEvent.ACTION_DOWN) ||
            (event.getKeyCode() == android.view.KeyEvent.KEYCODE_BACK && event.isLongPress())) {
            nativeSendQuit();
            return true;
        }
        return super.dispatchKeyEvent(event);
    }
    @Override public void onDestroy() {
        super.onDestroy();
        android.os.Process.killProcess(android.os.Process.myPid());
    }
}

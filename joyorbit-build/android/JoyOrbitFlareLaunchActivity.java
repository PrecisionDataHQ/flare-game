package io.precisiondata.joyorbit.flare;

import android.app.Activity;
import android.os.Bundle;
import java.io.*;

public final class JoyOrbitFlareLaunchActivity extends Activity {
    private volatile boolean cancelled;
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        android.widget.TextView label = new android.widget.TextView(this);
        label.setText("Starting Flare…");
        label.setTextColor(0xff8ee5c0);
        label.setTextSize(28);
        label.setGravity(android.view.Gravity.CENTER);
        label.setBackgroundColor(0xff0e1014);
        setContentView(label);
        new Thread(() -> {
            try {
                File root = new File(getFilesDir(), "joyorbit/flare");
                File data = new File(root, "data");
                File stamp = new File(data, ".source-2ef474f5-1.15");
                if (!stamp.isFile()) {
                    copyTree("joyorbit/flare/data", data);
                    try (FileOutputStream output = new FileOutputStream(stamp)) { output.write(1); }
                }
                new File(root, "userdata/saves").mkdirs();
                new File(root, "userdata/mods").mkdirs();
                new File(root, "config").mkdirs();
                File settings = new File(root, "config/settings.txt");
                if (!settings.isFile()) {
                    File defaults = new File(data, "mods/default/engine/default_settings.txt");
                    try (FileOutputStream output = new FileOutputStream(settings)) {
                        if (defaults.isFile()) {
                            try (InputStream input = new FileInputStream(defaults)) {
                                byte[] buffer = new byte[8192]; int count;
                                while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
                            }
                        }
                        boolean tv = (getResources().getConfiguration().uiMode & android.content.res.Configuration.UI_MODE_TYPE_MASK)
                            == android.content.res.Configuration.UI_MODE_TYPE_TELEVISION;
                        String firstRun = "\nlanguage=en\nsetup_language=1\nsetup_mousemove=1\nresolution_w=1280\nresolution_h=720\nenable_joystick=1\ndpi_scaling=" + (tv ? "0" : "1") + "\ntouch_controls=" + (tv ? "0" : "1") + "\nno_mouse=" + (tv ? "1" : "0") + "\n";
                        output.write(firstRun.getBytes(java.nio.charset.StandardCharsets.UTF_8));
                    }
                }

                runOnUiThread(() -> {
                    if (cancelled) return;
                    startActivity(new android.content.Intent(this, JoyOrbitFlareActivity.class));
                    finish();
                });
            } catch (IOException failure) {
                android.util.Log.e("JoyOrbit", "Flare data preparation failed", failure);
                runOnUiThread(() -> label.setText("Flare could not start. Return to the library and try again."));
            }
        }, "JoyOrbit Flare data").start();
    }
    private void copyTree(String asset, File target) throws IOException {
        String[] children = getAssets().list(asset);
        if (children != null && children.length > 0) {
            if (!target.isDirectory() && !target.mkdirs()) throw new IOException("Cannot create game data directory");
            for (String name : children) copyTree(asset + "/" + name, new File(target, name));
        } else {
            File parent = target.getParentFile();
            if (!parent.isDirectory() && !parent.mkdirs()) throw new IOException("Cannot create game data directory");
            File temporary = new File(parent, target.getName() + ".new");
            try (InputStream input = getAssets().open(asset); FileOutputStream output = new FileOutputStream(temporary)) {
                byte[] buffer = new byte[65536];
                int count;
                while ((count = input.read(buffer)) != -1) output.write(buffer, 0, count);
            }
            if (!temporary.renameTo(target)) throw new IOException("Cannot finish game data extraction");
        }
    }
    @Override public void onDestroy() { cancelled = true; super.onDestroy(); }
}

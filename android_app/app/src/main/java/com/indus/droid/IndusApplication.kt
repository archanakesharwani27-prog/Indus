package com.indus.droid

import android.app.Application
import timber.log.Timber

class IndusApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        if (BuildConfig.DEBUG) {
            Timber.plant(Timber.DebugTree())
        }
    }
}
package com.kiosk;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class KioskApplication {
    public static void main(String[] args) {
        SpringApplication.run(KioskApplication.class, args);
    }
}

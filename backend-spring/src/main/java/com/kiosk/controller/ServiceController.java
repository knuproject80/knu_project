package com.kiosk.controller;

import com.kiosk.dto.request.ApplicationCreateRequest;
import com.kiosk.dto.response.ApiResponse;
import com.kiosk.entity.CivilApplication;
import com.kiosk.entity.ServiceItem;
import com.kiosk.repository.CivilApplicationRepository;
import com.kiosk.repository.ServiceItemRepository;
import jakarta.validation.Valid;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

@RestController
@RequestMapping("/api")
public class ServiceController {

    private static final Logger log = LoggerFactory.getLogger(ServiceController.class);

    private final ServiceItemRepository serviceItemRepository;
    private final CivilApplicationRepository applicationRepository;

    /** 접수번호 순번 — AtomicInteger 로 동시 요청 시 충돌 방지 */
    private final AtomicInteger applicationSeq = new AtomicInteger(1);

    public ServiceController(ServiceItemRepository serviceItemRepository,
                             CivilApplicationRepository applicationRepository) {
        this.serviceItemRepository = serviceItemRepository;
        this.applicationRepository = applicationRepository;
    }

    // GET /api/services
    @GetMapping("/services")
    public ResponseEntity<ApiResponse<List<ServiceItem>>> getAllServices() {
        List<ServiceItem> services =
                serviceItemRepository.findByIsAvailableTrueOrderBySortOrder();
        return ResponseEntity.ok(ApiResponse.ok(services));
    }

    // GET /api/services/category/{categoryId}
    @GetMapping("/services/category/{categoryId}")
    public ResponseEntity<ApiResponse<List<ServiceItem>>> getServicesByCategory(
            @PathVariable Long categoryId) {
        List<ServiceItem> services =
                serviceItemRepository.findByCategoryIdOrderBySortOrder(categoryId);
        return ResponseEntity.ok(ApiResponse.ok(services));
    }

    // POST /api/applications
    @PostMapping("/applications")
    public ResponseEntity<ApiResponse<Map<String, Object>>> createApplication(
            @Valid @RequestBody ApplicationCreateRequest request) {

        String today = LocalDateTime.now()
                .format(DateTimeFormatter.ofPattern("yyyyMMdd"));

        // 최대 3번 재시도 (unique 충돌 대비)
        CivilApplication saved = null;
        String applicationNo = null;
        for (int attempt = 0; attempt < 3; attempt++) {
            applicationNo = "CIV-" + today + "-"
                    + String.format("%04d", applicationSeq.getAndIncrement());

            CivilApplication application = CivilApplication.builder()
                    .applicationNo(applicationNo)
                    .sessionId(request.getSessionId())
                    .serviceItemId(request.getServiceItemId())
                    .applicantName(request.getApplicantName())
                    .copies(request.getCopies() != null ? request.getCopies() : 1)
                    .purpose(request.getPurpose())
                    .feePaid(request.getFeePaid() != null ? request.getFeePaid() : 0)
                    .build();
            try {
                saved = applicationRepository.save(application);
                break;
            } catch (Exception e) {
                log.warn("접수번호 충돌 재시도 {}/3: {}", attempt + 1, applicationNo);
                if (attempt == 2) throw e;
            }
        }

        log.info("민원 접수: applicationNo={}, sessionId={}", applicationNo, request.getSessionId());

        Map<String, Object> result = new HashMap<>();
        result.put("applicationNo", applicationNo);
        return ResponseEntity.ok(ApiResponse.ok("민원이 정상적으로 접수되었습니다", result));
    }

    // GET /api/applications/{applicationNo}
    @GetMapping("/applications/{applicationNo}")
    public ResponseEntity<ApiResponse<Map<String, Object>>> getApplication(
            @PathVariable String applicationNo) {

        return applicationRepository.findByApplicationNo(applicationNo)
                .map(app -> {
                    Map<String, Object> result = new HashMap<>();
                    result.put("applicationNo", app.getApplicationNo());
                    result.put("status", app.getStatus());
                    result.put("copies", app.getCopies());
                    result.put("purpose", app.getPurpose() != null ? app.getPurpose() : "");
                    result.put("feePaid", app.getFeePaid());
                    result.put("createdAt", app.getCreatedAt().toString());
                    return ResponseEntity.ok(ApiResponse.ok(result));
                })
                .orElse(ResponseEntity.ok(
                        ApiResponse.error("해당 접수번호를 찾을 수 없습니다: " + applicationNo)));
    }

    // GET /api/applications/session/{sessionId}
    @GetMapping("/applications/session/{sessionId}")
    public ResponseEntity<ApiResponse<List<CivilApplication>>> getApplicationsBySession(
            @PathVariable String sessionId) {
        List<CivilApplication> apps = applicationRepository.findBySessionId(sessionId);
        return ResponseEntity.ok(ApiResponse.ok(apps));
    }
}

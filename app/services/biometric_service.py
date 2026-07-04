from abc import ABC, abstractmethod
from math import sqrt


class AttendanceVerificationProvider(ABC):
    @abstractmethod
    def verify(self, payload: dict | None = None) -> dict:
        raise NotImplementedError


class ManualVerificationProvider(AttendanceVerificationProvider):
    def verify(self, payload: dict | None = None) -> dict:
        return {
            "verification_status": "approved",
            "provider": "manual",
            "details": payload or {},
        }


class FaceRecognitionVerificationProvider(AttendanceVerificationProvider):
    def verify(self, payload: dict | None = None) -> dict:
        if not payload:
            raise ValueError("بيانات التحقق بالوجه مطلوبة.")
        return {
            "verification_status": "approved",
            "provider": "face",
            "details": payload,
        }


class FaceRecognitionMatcher:
    def average_descriptors(self, descriptors: list[list[float]]) -> list[float]:
        if not descriptors:
            raise ValueError("لا توجد عينات وجه صالحة للتسجيل.")
        descriptor_length = len(descriptors[0])
        if descriptor_length != 128:
            raise ValueError("بصمة الوجه يجب أن تحتوي على 128 قيمة.")
        for descriptor in descriptors:
            if len(descriptor) != descriptor_length:
                raise ValueError("جميع عينات الوجه يجب أن تكون بنفس الطول.")
        return [
            round(sum(descriptor[index] for descriptor in descriptors) / len(descriptors), 8)
            for index in range(descriptor_length)
        ]

    def distance(self, source_descriptor: list[float], candidate_descriptor: list[float]) -> float:
        if len(source_descriptor) != 128 or len(candidate_descriptor) != 128:
            raise ValueError("بصمة الوجه غير صالحة.")
        return sqrt(
            sum((float(source_value) - float(candidate_value)) ** 2 for source_value, candidate_value in zip(source_descriptor, candidate_descriptor))
        )


class VerificationProviderFactory:
    def create(self, source_type: str) -> AttendanceVerificationProvider:
        if source_type == "manual":
            return ManualVerificationProvider()
        if source_type == "face":
            return FaceRecognitionVerificationProvider()
        return ManualVerificationProvider()

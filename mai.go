package main

import (
	"fmt"
	"time"
)

// TimeChecker 工作时间检查器
type TimeChecker struct {
	StartHour int // 开始小时(0-23)
	EndHour   int // 结束小时(0-23)
}

// NewTimeChecker 创建时间检查器
func NewTimeChecker(startHour, endHour int) *TimeChecker {
	return &TimeChecker{
		StartHour: startHour,
		EndHour:   endHour,
	}
}

// IsActive 当前时间是否在设定范围内
func (tc *TimeChecker) IsActive() bool {
	return tc.isTimeInRange(time.Now())
}

// isTimeInRange 核心判断逻辑
func (tc *TimeChecker) isTimeInRange(t time.Time) bool {
	currentHour := t.Hour()

	// 处理跨天情况(如22:00-5:00)
	if tc.StartHour > tc.EndHour {
		return currentHour >= tc.StartHour || currentHour < tc.EndHour
	}

	// 处理同一天情况(如9:00-18:00)
	return currentHour >= tc.StartHour && currentHour < tc.EndHour
}



func main() {
	// 示例1：创建9:00-18:00的检查器
	dayShift := NewTimeChecker(14, 22)

	if dayShift.IsActive() {
		fmt.Println("现在是白班工作时间")
	} else {
		fmt.Println("现在是白班休息时间")
	}

}

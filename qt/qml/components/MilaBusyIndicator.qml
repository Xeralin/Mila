import QtQuick
import QtQuick.Controls.Basic
import ".."

BusyIndicator {
    id: control

    implicitWidth: 32
    implicitHeight: 32
    padding: 0

    contentItem: Canvas {
        id: arc

        implicitWidth: 32
        implicitHeight: 32
        opacity: control.running ? 1.0 : 0.0
        Behavior on opacity { NumberAnimation { duration: 150 } }

        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            const size = Math.min(width, height)
            const line = Math.max(3, size / 10)
            ctx.lineWidth = line
            ctx.strokeStyle = Theme.accent
            ctx.beginPath()
            ctx.arc(width / 2, height / 2, size / 2 - line, 0, Math.PI * 1.5)
            ctx.stroke()
        }

        RotationAnimation on rotation {
            running: control.running && control.visible
            from: 0
            to: 360
            duration: 900
            loops: Animation.Infinite
        }
    }
}

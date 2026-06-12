import QtQuick
import QtQuick.Controls.Basic
import ".."

ProgressBar {
    id: control

    implicitHeight: 6
    padding: 0

    background: Rectangle {
        implicitWidth: 200
        implicitHeight: 6
        radius: Theme.radius_small
        color: Theme.field
        border.width: 1
        border.color: Theme.border
    }

    contentItem: Item {
        implicitWidth: 200
        implicitHeight: 6
        clip: true

        Rectangle {
            visible: !control.indeterminate
            width: Math.round(control.visualPosition * parent.width)
            height: parent.height
            radius: Theme.radius_small
            color: Theme.accent
        }

        Rectangle {
            id: runner
            visible: control.indeterminate
            width: Math.max(40, Math.round(parent.width * 0.25))
            height: parent.height
            radius: Theme.radius_small
            color: Theme.accent

            NumberAnimation on x {
                running: control.indeterminate && control.visible
                from: -runner.width
                to: control.availableWidth
                duration: 1100
                loops: Animation.Infinite
            }
        }
    }
}
